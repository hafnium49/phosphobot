"""
Harness of the servo compensation tests: the S1a endpoint harness (two real
SO100Hardware objects whose motors bus is a FakeBus, in a bare FastAPI app), the
real compensation config file as a fixture, and a clock and rest timers that the
tests drive.

The guard of tests/phosphobot/conftest.py applies here as everywhere under
tests/phosphobot: no test can open a port or connect to the rig's services.
"""

import asyncio
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict

import numpy as np
import pytest

# The S1a fixtures, made visible to this directory
from s1a.conftest import (  # noqa: F401
    LEFT_SERIAL,
    RIGHT_SERIAL,
    FakeRCM,
    arm_factory,
    arms,
    client,
    client_for,
    hardware_mode,
    only_simulation,
)

from phosphobot import compensated_write, teleoperation
from phosphobot.endpoints import control
from phosphobot.hardware import SO100Hardware, base, so100
from phosphobot.hardware import servo_compensation as sc

CONFIG = Path(__file__).parent / "so101_compensation_v1.json"
REAL_REST_TIMER = compensated_write.RestTimer
RIGHT = {"serial": RIGHT_SERIAL}
LEFT = {"serial": LEFT_SERIAL}
# A pose at which the model has something to say on every arm joint
Q = [0.2, -0.6, 0.9, 0.4, -0.3, 0.05]
DT = 1 / 15


@pytest.fixture(autouse=True)
def server_without_compensation(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Each test starts as a server does: the variables unset, nothing loaded. (The
    rig's own STOP files must never reach a test through the environment.)
    """
    monkeypatch.delenv(compensated_write.ENV_VAR, raising=False)
    monkeypatch.delenv(compensated_write.STOP_ENV_VAR, raising=False)
    monkeypatch.setattr(compensated_write, "_config", None)


@pytest.fixture
def config_file(monkeypatch: pytest.MonkeyPatch) -> Path:
    """The server was started with the variable naming the real config file."""
    monkeypatch.setenv(compensated_write.ENV_VAR, str(CONFIG))
    return CONFIG


class Clock:
    """Stands in for time.monotonic in the compensated write path."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> float:
        self.t += seconds
        return self.t


class FakeTimer:
    """
    Stands in for compensated_write.RestTimer: the test is the event loop. fire()
    runs the callback as the loop would, also for a timer that was cancelled (a
    callback the loop had already taken must do nothing either).
    """

    def __init__(self, made: list, delay_s: float, callback: Callable) -> None:
        self.delay_s, self.callback, self.cancelled = delay_s, callback, False
        made.append(self)

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self) -> None:
        self.callback()


@pytest.fixture(autouse=True)
def timers(monkeypatch: pytest.MonkeyPatch) -> list:
    """Every rest timer the server made, in order. None runs by itself."""
    made: list = []
    monkeypatch.setattr(
        compensated_write,
        "RestTimer",
        lambda delay_s, callback: FakeTimer(made, delay_s, callback),
    )
    return made


@pytest.fixture
def real_timers(timers: list, monkeypatch: pytest.MonkeyPatch) -> list:
    """
    The timers are the server's own, on the event loop of the test client. Returns
    the RestTimer objects it made, in order.
    """
    made: list = []

    def make(delay_s: float, callback: Callable) -> Any:
        made.append(REAL_REST_TIMER(delay_s, callback))
        return made[-1]

    monkeypatch.setattr(compensated_write, "RestTimer", make)
    return made


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()
    monkeypatch.setattr(compensated_write, "now", clock)
    return clock


def compensator(serial: str = RIGHT_SERIAL) -> sc.Compensator:
    return sc.Compensator.from_config(CONFIG, serial)


def units(arm: SO100Hardware, q_rad: list) -> list:
    """Radians to motor units, the way the fork converts them for a write."""
    return arm._radians_vec_to_motor_units(np.array(q_rad, dtype=float)).tolist()


def write(client, angles, terms="full", arm=RIGHT, final=None, **body):  # type: ignore
    """
    POST /joints/write?compensate=<terms> of six angles in radians; with `final`,
    also &final=<final>.
    """
    params = {**arm, "compensate": terms}
    if final is not None:
        params["final"] = final
    return client.post(
        "/joints/write", params=params, json={"angles": angles, "unit": "rad", **body}
    )


def lags(comp: sc.Compensator) -> np.ndarray:
    return np.array([comp.params[name]["lag_s"] for name in sc.JOINTS])


def speed_ticks(comp: sc.Compensator, dq_rad: list) -> np.ndarray:
    """The commanded speed of the five arm joints, ticks/s, for a step dq every DT."""
    return np.array(comp.signs[:5]) * sc.K * np.array(dq_rad[:5], dtype=float) / DT


def lead_of_a_line(comp: sc.Compensator, dq_rad: list, n: int) -> np.ndarray:
    """
    The lead (ticks) in the command of the n-th moving request of a line that starts
    from rest: lag x speed, reached by at most LEAD_SLEW_TICKS (4) a request.
    """
    full = lags(comp) * speed_ticks(comp, dq_rad)
    return np.sign(full) * np.minimum(n * sc.LEAD_SLEW_TICKS, np.abs(full))


def command_with_lead(comp, q, lead_ticks, side, terms=sc.TERMS) -> list:  # type: ignore
    """
    The command for request q whose lead is `lead_ticks` and whose friction side is
    `side`: the model's equation alone (no Stream), at the speed that gives this lead.
    """
    return comp.command(q, np.array(lead_ticks, dtype=float) / lags(comp), side, terms)


# The step of start_stream and of line(): the base and the shoulder lift at 0.3 rad/s
DQ = [0.02, -0.02, 0.0, 0.0, 0.0, 0.0]


def line(client, clock, n, dq=DQ, start=Q, arm=RIGHT, terms="full") -> list:  # type: ignore
    """
    A first request at `start`, then n requests, each `dq` further and DT later.
    Returns the last request.
    """
    assert write(client, start, terms=terms, arm=arm).status_code == 200
    q = list(start)
    for _ in range(n):
        q = [angle + step for angle, step in zip(q, dq)]
        clock.advance(DT)
        assert write(client, q, terms=terms, arm=arm).status_code == 200
    return q


def goal(arm: SO100Hardware) -> list:
    return list(arm.motors_bus.regs["Goal_Position"])


def goal_writes(arm: SO100Hardware) -> int:
    return arm.motors_bus.calls.count(("write", "Goal_Position"))


def start_stream(client, clock, arm=RIGHT, terms="full") -> list:  # type: ignore
    """
    Two compensated requests, the second one moving: the stream has a speed and a
    direction, and its last command carries them (of the lead, lag x speed, the 4
    ticks that one request brings in). Returns the last request.
    """
    assert write(client, Q, terms=terms, arm=arm).status_code == 200
    q = list(Q)
    q[0] += 0.02
    q[1] -= 0.02
    clock.advance(DT)
    assert write(client, q, terms=terms, arm=arm).status_code == 200
    return q


class _RealExceptSleep:
    """A module's `asyncio` or `time`: the real one, except that sleeps return at once."""

    def __init__(self, real: Any) -> None:
        self._real = real

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class _Asyncio(_RealExceptSleep):
    async def sleep(self, delay: float, result: Any = None) -> Any:
        return await asyncio.sleep(0, result)


class _Time(_RealExceptSleep):
    def sleep(self, seconds: float) -> None:
        return None


@pytest.fixture
def no_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    For the tests that call the fork's movers: their waits for the arm (0.1 to 1 s
    each) return at once, and move_to_initial_position does not load a calibration
    over the test's (init_config reads ~/phosphobot/calibration by serial).
    """
    for module in (base, control, teleoperation):
        monkeypatch.setattr(module, "asyncio", _Asyncio(asyncio))
    monkeypatch.setattr(so100, "time", _Time(time))
    monkeypatch.setattr(SO100Hardware, "init_config", lambda self: None)


def _post(path: str, **kwargs: Any) -> Callable:
    def call(client: Any, arm: SO100Hardware) -> None:
        r = client.post(path, params=RIGHT, **kwargs)
        assert r.status_code == 200, r.text

    return call


def _in_another_thread(client: Any, arm: SO100Hardware) -> None:
    thread = threading.Thread(
        target=arm.set_motors_positions, args=(np.zeros(6),), kwargs={"enable_gripper": True}
    )
    thread.start()
    thread.join()


def _while_off_the_bus(client: Any, arm: SO100Hardware) -> None:
    arm.is_connected = False
    assert arm.write_group_motor_position(np.array([2048] * 6)) is False


TELEOP = {"x": 0, "y": 0, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 1}

# Everything else that writes the goal of an arm: the endpoints, and under them the
# methods of the arm that every other mover of the fork goes through (teleoperation,
# leader-follower and gravity loops, playback, AI control).
OTHER_WRITERS: Dict[str, Callable] = {
    "joints/write": _post("/joints/write", json={"angles": Q, "unit": "rad"}),
    "torque/toggle off": _post("/torque/toggle", json={"torque_status": False}),
    "torque/toggle on": _post("/torque/toggle", json={"torque_status": True}),
    "move/init": _post("/move/init"),
    "move/absolute": _post("/move/absolute", json={"x": 0, "y": 0, "z": 0, "max_trials": 1}),
    "move/relative": _post("/move/relative", json={"x": 1, "y": 0, "z": 0}),
    "move/relative gripper": _post("/move/relative", json={"open": 1}),
    "move/sleep": _post("/move/sleep"),
    "move/hello": _post("/move/hello"),
    "move/teleop": _post("/move/teleop", json=TELEOP),
    "calibrate": _post("/calibrate"),
    "robot/disconnect": _post("/robot/disconnect"),
    "write_motor_position": lambda client, arm: arm.write_motor_position(6, 2048),
    "write_group_motor_position": lambda client, arm: arm.write_group_motor_position(
        np.array([2048] * 6)
    ),
    "set_motors_positions": lambda client, arm: arm.set_motors_positions(np.zeros(6)),
    "write_joint_positions": lambda client, arm: arm.write_joint_positions(
        [0.0] * 6, unit="rad"
    ),
    "control_gripper": lambda client, arm: arm.control_gripper(1.0),
    "enable_torque": lambda client, arm: arm.enable_torque(),
    "disable_torque": lambda client, arm: arm.disable_torque(),
    "calibrate_motors": lambda client, arm: arm.calibrate_motors(),
    "disconnect": lambda client, arm: arm.disconnect(),
    "another thread": _in_another_thread,
    "a write while off the bus": _while_off_the_bus,
}
