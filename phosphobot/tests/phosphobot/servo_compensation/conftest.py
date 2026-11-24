"""
Harness of the servo compensation tests: the S1a endpoint harness (two real
SO100Hardware objects whose motors bus is a FakeBus, in a bare FastAPI app), the
real compensation config file as a fixture, and a clock the tests set.

The guard of tests/phosphobot/conftest.py applies here as everywhere under
tests/phosphobot: no test can open a port or connect to the rig's services.
"""

from pathlib import Path

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

from phosphobot import compensated_write
from phosphobot.hardware import SO100Hardware
from phosphobot.hardware import servo_compensation as sc

CONFIG = Path(__file__).parent / "so101_compensation_v1.json"
RIGHT = {"serial": RIGHT_SERIAL}
LEFT = {"serial": LEFT_SERIAL}
# A pose at which the model has something to say on every arm joint
Q = [0.2, -0.6, 0.9, 0.4, -0.3, 0.05]
DT = 1 / 15


@pytest.fixture(autouse=True)
def server_without_compensation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts as a server does: the variable unset, nothing loaded."""
    monkeypatch.delenv(compensated_write.ENV_VAR, raising=False)
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


def write(client, angles, terms="full", arm=RIGHT, **body):  # type: ignore
    """POST /joints/write?compensate=<terms> of six angles in radians."""
    return client.post(
        "/joints/write",
        params={**arm, "compensate": terms},
        json={"angles": angles, "unit": "rad", **body},
    )


def goal(arm: SO100Hardware) -> list:
    return list(arm.motors_bus.regs["Goal_Position"])


def goal_writes(arm: SO100Hardware) -> int:
    return arm.motors_bus.calls.count(("write", "Goal_Position"))
