"""
Opt-in servo compensation of POST /joints/write (compensate=full|static).

A measured model of the servos predicts where each arm joint ends relative to its
command. The compensated write sends the request minus that predicted error, so the
servo ends on the request. The model's equation and the stream that turns successive
requests into commands are phosphobot.hardware.servo_compensation, a verbatim copy
from another repository. This module is what the server adds around it:

- the config file named by the environment variable PHOSPHOBOT_SERVO_COMPENSATION,
  loaded once, at the first request that asks for compensation;
- per arm, held by the arm object (ArmCompensation): one stream per set of terms,
  the last compensated request and the timer of the rest command. Anything else that
  writes the arm's goal voids them (SO100Hardware._goal_written is where every such
  write passes);
- the rest command: the last command of a moving "full" stream carries lag x speed,
  and a servo left with it rests past the request. A one-shot timer on the event
  loop writes the stream's rest command when no further request comes;
- the refusals. Every reason a request cannot be compensated is an HTTPException and
  nothing is written: there is no fallback to an uncompensated write.

See docs/servo_compensation.md, next to the package.
"""

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

import numpy as np
from fastapi import HTTPException
from loguru import logger

from phosphobot.hardware import servo_compensation as sc
from phosphobot.hardware.so100 import SO100Hardware

ENV_VAR = "PHOSPHOBOT_SERVO_COMPENSATION"

Terms = Literal["full", "static"]
TERMS: Dict[str, Tuple[str, ...]] = {"full": sc.TERMS, "static": sc.STATIC}

# The rest command is written when no compensated request came for this long:
# 1.5 x the stream's usual interval between requests, within these bounds
REST_DELAY_MIN_S = 0.08
REST_DELAY_MAX_S = 0.30

# The clock of the streams. A name of this module, so that tests can set the time
now = time.monotonic


def usual_interval_s(stream: sc.Stream) -> float:
    """
    The stream's usual time between two requests: the median of its last intervals,
    which is what it takes its speed over. MAX_DT_S for a stream that has none yet
    (a first step, or requests further apart than MAX_DT_S), as the stream does.
    """
    intervals = stream._intervals
    return float(np.median(intervals)) if intervals else sc.MAX_DT_S


def rest_delay_s(stream: sc.Stream) -> float:
    """REST_DELAY_S of this stream now."""
    return float(
        np.clip(1.5 * usual_interval_s(stream), REST_DELAY_MIN_S, REST_DELAY_MAX_S)
    )


class RestTimer:
    """
    A one-shot timer on the running event loop: the one the endpoints run on, since
    it is made during a request. cancel() may be called from any thread.
    """

    def __init__(self, delay_s: float, callback: Callable[[], None]) -> None:
        self._loop = asyncio.get_running_loop()
        self._handle = self._loop.call_later(delay_s, callback)

    def cancel(self) -> None:
        try:
            on_the_loop = asyncio.get_running_loop() is self._loop
        except RuntimeError:
            on_the_loop = False
        if on_the_loop:
            self._handle.cancel()
            return
        try:
            self._loop.call_soon_threadsafe(self._handle.cancel)
        except RuntimeError:
            # The loop is closed: its timers will not fire
            pass


@dataclass
class _Config:
    """What the one load of the config file gave: compensators by serial, or why not."""

    path: Optional[str]
    compensators: Dict[str, sc.Compensator] = field(default_factory=dict)
    status_code: int = 200
    error: Optional[str] = None


# None until the first request that asks for compensation
_config: Optional[_Config] = None


def _load() -> _Config:
    """
    Read the config file the variable names. Never raises: what went wrong is kept
    and answered to every request that asks for compensation.
    """
    path = os.environ.get(ENV_VAR)
    if not path:
        logger.info(f"Servo compensation was asked for, but {ENV_VAR} is unset")
        return _Config(
            path=None,
            status_code=409,
            error=f"servo compensation is not configured on this server ({ENV_VAR} is unset)",
        )
    try:
        cfg = json.loads(Path(path).read_text())
        schema = cfg.get("schema") if isinstance(cfg, dict) else None
        if schema != sc.CONFIG_SCHEMA:
            raise ValueError(f"schema {schema!r}, this server reads {sc.CONFIG_SCHEMA}")
        compensators = {
            serial: sc.Compensator.from_config(Path(path), serial)
            for serial in cfg.get("arms", {})
        }
    except Exception as e:
        logger.error(
            f"Servo compensation config {path} cannot be used: {type(e).__name__}: {e}. "
            "Requests that ask for compensation are refused until the server is restarted."
        )
        return _Config(
            path=path,
            status_code=500,
            error=f"servo compensation config {path} cannot be used: {type(e).__name__}: {e}",
        )
    logger.info(
        f"Servo compensation config loaded from {path}: schema {schema}, "
        f"model {cfg.get('model_file')} {cfg.get('model_version')}, "
        f"arms {sorted(compensators)}, at most {cfg.get('max_ticks', sc.MAX_TICKS)} ticks per joint"
    )
    return _Config(path=path, compensators=compensators)


def _calibration_difference(
    robot: SO100Hardware, compensator: sc.Compensator
) -> Optional[str]:
    """
    How the arm's loaded calibration differs from the signs and offsets the model
    was fitted with. None when the six signs and the six offsets are the same numbers.
    """
    if robot.config is None:
        return "the arm has no calibration loaded"
    differences = []
    for name, want in (
        ("servos_offsets_signs", compensator.signs),
        ("servos_offsets", compensator.offsets),
    ):
        have = [float(value) for value in getattr(robot.config, name)]
        if have != want:
            differences.append(f"{name} {have} is not the config's {want}")
    if differences:
        return "the loaded calibration is not the one of the servo compensation config: " + "; ".join(
            differences
        )
    return None


def compensator_for(robot: Any, serial: Optional[str]) -> sc.Compensator:
    """
    The compensator of this arm, or the refusal: the variable unset (409), a config
    file that cannot be used (500), a robot that is not an SO-100/SO-101 (400), an
    arm that is not in the config or whose calibration is not the config's (409).
    """
    global _config
    if _config is None:
        _config = _load()
    if _config.error is not None:
        raise HTTPException(status_code=_config.status_code, detail=_config.error)
    if not isinstance(robot, SO100Hardware):
        raise HTTPException(
            status_code=400, detail="Robot does not support servo compensation"
        )
    compensator = _config.compensators.get(serial or "")
    if compensator is None:
        raise HTTPException(
            status_code=409,
            detail=f"arm {serial} is not in the servo compensation config {_config.path} (its arms: {sorted(_config.compensators)})",
        )
    difference = _calibration_difference(robot, compensator)
    if difference is not None:
        raise HTTPException(status_code=409, detail=f"arm {serial}: {difference}")
    return compensator


class ArmCompensation:
    """
    What the server keeps for one arm. The arm object holds it
    (SO100Hardware.servo_compensation), so an arm that is found again after a USB
    drop starts with none.

    - streams: one per set of terms ("full", "static")
    - terms, requested_position: the terms of the last compensated request, and that
      request in motor units, converted the way the arm converts radians. Both None
      when the arm's last goal write was not a compensated one.
    - the rest timer: at most one, pending while the last command of the "full"
      stream carries a speed term. A new compensated request and void() cancel it.

    The endpoints write from the event loop, and some movers of the server from a
    thread of their own (the leader-follower loop, a gripper command in a background
    task). The lock makes a write of theirs wait for a compensated write in
    progress and void it afterwards.
    """

    def __init__(self, robot: SO100Hardware) -> None:
        self.robot = robot
        self.streams: Dict[str, sc.Stream] = {}
        self.terms: Optional[str] = None
        self.requested_position: Optional[List[int]] = None
        self._lock = threading.RLock()
        # True while this object writes the arm's goal itself
        self._own_write = False
        self._rest_timer: Optional[RestTimer] = None
        # Changes whenever the rest timer is cancelled: a callback of another
        # generation, which the loop could not be kept from running, does nothing
        self._generation = 0

    def goal_written(self) -> None:
        """
        SO100Hardware._goal_written: something writes this arm's goal or switches
        its torque, or the arm is disconnected. Unless it is this object's own
        write, the streams are void.
        """
        with self._lock:
            if not self._own_write:
                self.void()

    def void(self) -> None:
        """What the streams knew is void: the arm's goal is not theirs any more."""
        with self._lock:
            self._cancel_rest()
            for stream in self.streams.values():
                stream.reset()
            self.terms = None
            self.requested_position = None

    def _cancel_rest(self) -> None:
        self._generation += 1
        timer, self._rest_timer = self._rest_timer, None
        if timer is not None:
            timer.cancel()

    def _rest(self, stream: sc.Stream, generation: int) -> None:
        """
        The rest timer's callback, on the event loop: no compensated request came
        for REST_DELAY_S, the stream has stopped. Write its rest command, once.

        Nothing is written for an arm that is off the bus or whose torque is not
        on for all servos. A rest command that was not written is logged and voids
        the streams; nothing is raised into the event loop.
        """
        with self._lock:
            if generation != self._generation:
                return
            self._generation += 1
            self._rest_timer = None
            serial = getattr(self.robot, "SERIAL_ID", None)
            try:
                if not self.robot.is_connected:
                    raise ConnectionError("the arm is not on the bus")
                # Read from the bus now: torque can go off without the server.
                # A read that failed is tried once more
                torque_enabled, _ = self.robot.read_torque_enabled(max_age_s=0)
                if torque_enabled is None:
                    torque_enabled, _ = self.robot.read_torque_enabled(max_age_s=0)
                if torque_enabled is None or not all(torque_enabled):
                    raise ConnectionError(f"Torque_Enable is {torque_enabled}")
                command = stream.rest(now())
                if command is None:
                    return
                if self._write_own(command) is not True:
                    raise ConnectionError("bus write failed")
            except Exception as e:
                logger.warning(
                    f"Servo compensation: the rest command of arm {serial} was not written: {e}"
                )
                self.void()

    def _write_own(self, command: List[float]) -> Optional[bool]:
        """Write a command of a stream through the arm's usual path of a write in radians."""
        self._own_write = True
        try:
            return self.robot.write_joint_positions(angles=command, unit="rad")
        finally:
            self._own_write = False

    def write(
        self, compensator: sc.Compensator, angles: List[float], terms: Terms
    ) -> Tuple[Optional[bool], List[int]]:
        """
        Write the command of the stream for this request (six angles in radians).

        Returns what became of the bus write, as write_joint_positions, and what
        was added to each of the five arm joints, in motor units as written.

        Called on the event loop (the endpoints are coroutines): the rest timer
        is made on the running loop.
        """
        robot = self.robot
        with self._lock:
            self._cancel_rest()
            for name, other in self.streams.items():
                if name != terms:
                    # For a stream, a write with other terms is a write by somebody else
                    other.reset()
            stream = self.streams.get(terms)
            if stream is None:
                stream = self.streams[terms] = sc.Stream(compensator, TERMS[terms])

            command = stream.step(angles, now())
            try:
                done = self._write_own(command)
            except Exception:
                self.void()
                raise
            if done is not True:
                self.void()
                return done, []

            requested = robot._radians_vec_to_motor_units(np.array(angles, dtype=float))
            written = robot._radians_vec_to_motor_units(np.array(command, dtype=float))
            self.terms = terms
            self.requested_position = [int(units) for units in requested]
            if stream.pending:
                # The command carries a speed term that the rest command takes back
                self._rest_timer = RestTimer(
                    rest_delay_s(stream), partial(self._rest, stream, self._generation)
                )
            return done, [int(units) for units in (written - requested)[:5]]


def write(
    robot: Any, serial: Optional[str], angles: List[float], terms: Terms
) -> Tuple[Optional[bool], dict]:
    """
    The compensated write of POST /joints/write: six angles in radians.

    Returns what became of the bus write and the `compensation` field of the
    response. Raises the refusals of compensator_for, and 503 for an arm that is
    off the bus (also in only-simulation mode: the simulation has no servos).
    """
    compensator = compensator_for(robot, serial)
    if not robot.is_connected:
        raise HTTPException(status_code=503, detail=f"arm {serial} is not on the bus")
    if robot.servo_compensation is None:
        robot.servo_compensation = ArmCompensation(robot)
    done, added = robot.servo_compensation.write(compensator, angles, terms)
    return done, {"terms": terms, "correction_ticks": added}
