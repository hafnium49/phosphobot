"""
Opt-in servo compensation of POST /joints/write (compensate=full|static).

A measured model of the servos predicts where each arm joint ends relative to its
command. The compensated write sends the request minus that predicted error, so the
servo ends on the request. The model's equation and the stream that turns successive
requests into commands are phosphobot/hardware/servo_compensation.py, a verbatim
copy from another repository. This module is what the server adds around it:

- the config file named by the environment variable PHOSPHOBOT_SERVO_COMPENSATION,
  loaded once, at the first request that asks for compensation;
- per arm, held by the arm object (ArmCompensation): one stream per set of terms and
  the last compensated request;
- the refusals. Every reason a request cannot be compensated is an HTTPException and
  nothing is written: there is no fallback to an uncompensated write.

See phosphobot/docs/servo_compensation.md.
"""

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
from fastapi import HTTPException
from loguru import logger

from phosphobot.hardware import servo_compensation as sc
from phosphobot.hardware.so100 import SO100Hardware

ENV_VAR = "PHOSPHOBOT_SERVO_COMPENSATION"

Terms = Literal["full", "static"]
TERMS: Dict[str, Tuple[str, ...]] = {"full": sc.TERMS, "static": sc.STATIC}

# The clock of the streams. A name of this module, so that tests can set the time
now = time.monotonic


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
        logger.info(f"Servo compensation was asked for, but {ENV_VAR} is not set")
        return _Config(
            path=None,
            status_code=501,
            error=f"servo compensation is not available on this server: {ENV_VAR} is not set",
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
    The compensator of this arm, or the refusal: no usable config (501, 500), a
    robot that is not an SO-100/SO-101 (400), an arm that is not in the config or
    whose calibration is not the config's (409).
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
    """

    def __init__(self, robot: SO100Hardware) -> None:
        self.robot = robot
        self.streams: Dict[str, sc.Stream] = {}
        self.terms: Optional[str] = None
        self.requested_position: Optional[List[int]] = None

    def void(self) -> None:
        """What the streams knew is void: the arm's goal is not theirs any more."""
        for stream in self.streams.values():
            stream.reset()
        self.terms = None
        self.requested_position = None

    def write(
        self, compensator: sc.Compensator, angles: List[float], terms: Terms
    ) -> Tuple[Optional[bool], List[int]]:
        """
        Write the command of the stream for this request (six angles in radians).

        Returns what became of the bus write, as write_joint_positions, and what
        was added to each of the five arm joints, in motor units as written.
        """
        robot = self.robot
        for name, other in self.streams.items():
            if name != terms:
                # For a stream, a write with other terms is a write by somebody else
                other.reset()
        stream = self.streams.get(terms)
        if stream is None:
            stream = self.streams[terms] = sc.Stream(compensator, TERMS[terms])

        command = stream.step(angles, now())
        try:
            done = robot.write_joint_positions(angles=command, unit="rad")
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
