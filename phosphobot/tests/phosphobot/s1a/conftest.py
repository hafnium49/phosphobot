"""
Endpoint test harness for the S1a "truthful command API" work.

The two arms are real SO100Hardware objects whose motors bus is a FakeBus: no port
is ever opened (see the autouse guard in tests/phosphobot/conftest.py), and the
endpoints run in a bare FastAPI app, without phosphobot.app and its startup.
"""

import time
from typing import Any, Callable, Iterator, List, Optional, Union

import numpy as np
import pybullet
import pytest
from async_property import async_property
from fastapi import FastAPI
from fastapi.testclient import TestClient

from phosphobot.camera import get_all_cameras
from phosphobot.configs import config
from phosphobot.endpoints import control, recording
from phosphobot.hardware import SO100Hardware, get_sim
from phosphobot.recorder import get_recorder
from phosphobot.robot import RobotConnectionManager, get_rcm
from phosphobot.teleoperation import TeleopManager, get_teleop_manager

LEFT_SERIAL = "5A68011258"
RIGHT_SERIAL = "5A68009540"


class FakeBus:
    """
    Stands in for FeetechMotorsBus: six STS3215 registers in memory.

    - regs: register name -> one value per motor, in servo order
    - calls: every (operation, register) that reached the bus
    - fail: "read:<name>" / "write:<name>" raise ConnectionError, as a dead bus does
    - ignore: writes to these registers are accepted and not stored
    """

    def __init__(self) -> None:
        self.motors = dict(SO100Hardware.motors)
        self.is_connected = True
        self.regs: dict[str, list[int]] = {
            "Present_Position": [2048] * 6,
            "Goal_Position": [2048] * 6,
            "Torque_Enable": [1] * 6,
            "Present_Temperature": [30] * 6,
            "Max_Temperature_Limit": [70] * 6,
            "Present_Voltage": [120] * 6,
            "Present_Current": [0] * 6,
            "P_Coefficient": [16] * 6,
            "I_Coefficient": [0] * 6,
            "D_Coefficient": [32] * 6,
            "Lock": [1] * 6,
        }
        self.calls: list[tuple[str, str]] = []
        self.fail: set[str] = set()
        self.ignore: set[str] = set()

    @property
    def motor_names(self) -> list[str]:
        return list(self.motors.keys())

    @property
    def motor_models(self) -> list[str]:
        return [str(model) for _, model in self.motors.values()]

    def _indexes(self, motor_names: Optional[Union[List[str], str]]) -> list[int]:
        if motor_names is None:
            motor_names = self.motor_names
        if isinstance(motor_names, str):
            motor_names = [motor_names]
        return [self.motor_names.index(name) for name in motor_names]

    def read(
        self, data_name: str, motor_names: Optional[Union[List[str], str]] = None
    ) -> np.ndarray:
        self.calls.append(("read", data_name))
        if f"read:{data_name}" in self.fail:
            raise ConnectionError(f"Read failed due to communication error: {data_name}")
        return np.array([self.regs[data_name][i] for i in self._indexes(motor_names)])

    def write(
        self,
        data_name: str,
        values: Any,
        motor_names: Optional[Union[List[str], str]] = None,
    ) -> None:
        self.calls.append(("write", data_name))
        if f"write:{data_name}" in self.fail:
            raise ConnectionError(
                f"Write failed due to communication error: {data_name}"
            )
        indexes = self._indexes(motor_names)
        if isinstance(values, (int, float, np.integer)):
            values = [int(values)] * len(indexes)
        values = np.array(values).tolist()
        if len(values) != len(indexes):
            # FeetechMotorsBus._perform_write: zip(motor_ids, values, strict=True)
            raise ValueError("zip() arguments have different lengths")
        if data_name in self.ignore:
            return
        for i, value in zip(indexes, values):
            self.regs[data_name][i] = int(value)

    def read_with_motor_ids(
        self, motor_models: Any, motor_ids: Any, data_name: str, **kwargs: Any
    ) -> Any:
        self.calls.append(("read_with_motor_ids", data_name))
        if f"read:{data_name}" in self.fail:
            raise ConnectionError(f"Read failed due to communication error: {data_name}")
        if not isinstance(motor_ids, list):
            return self.regs[data_name][motor_ids - 1]
        return [self.regs[data_name][servo_id - 1] for servo_id in motor_ids]

    def disconnect(self) -> None:
        self.calls.append(("disconnect", ""))
        self.is_connected = False


def make_arm(serial: str, connected: bool = True) -> SO100Hardware:
    # only_simulation: default calibration, and no move registered at exit
    arm = SO100Hardware(only_simulation=True, serial_id=serial)
    arm.motors_bus = FakeBus()  # type: ignore
    # A real arm has the path of its port here. This one cannot be opened
    arm.device_name = f"/dev/fake-{serial}"
    arm.is_connected = connected
    arm._max_temperature_cache = {}
    return arm


class FakeRCM(RobotConnectionManager):
    """A RobotConnectionManager whose robots are the given list. It never scans."""

    def __init__(self, arms: list) -> None:
        super().__init__()
        self._all_robots = list(arms)

    def __del__(self) -> None:
        pass

    @async_property
    async def robots(self) -> list:  # type: ignore
        return self._all_robots


class _Port:
    def __init__(self, device: str) -> None:
        self.device = device


class RescanRCM(RobotConnectionManager):
    """
    A RobotConnectionManager whose next port scan finds other ports, as after a USB
    drop or re-attach: `robots` and `resolve` are the real ones, and the rebuilt
    list is `new`. Only the scan and the construction of the robots are faked.
    Nobody has scanned since the list was `old`.
    """

    def __init__(self, old: list, new: list) -> None:
        super().__init__()
        self._all_robots = list(old)
        self._new = list(new)
        self.available_ports = [_Port("/dev/fake0"), _Port("/dev/fake1")]  # type: ignore
        self.last_scan_time = 0  # more than 1 s ago: the next `robots` scans

    def __del__(self) -> None:
        pass

    def _scan_ports(self) -> tuple[list, list]:
        self.last_scan_time = time.time()
        return [_Port("/dev/fake2"), _Port("/dev/fake3")], []

    async def _find_robots(self) -> None:
        self._all_robots = list(self._new)


@pytest.fixture
def arm_factory(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., SO100Hardware]]:
    # The simulation is one world per process, stepped by a background thread. The
    # older tests of this suite read it while steps may still be pending, so these
    # tests ask for no steps and take their robots out of the world when they end.
    # They need no physics.
    monkeypatch.setattr(get_sim(), "step", lambda steps=60: None)
    made: list[SO100Hardware] = []

    def factory(serial: str, connected: bool = True) -> SO100Hardware:
        made.append(make_arm(serial, connected))
        return made[-1]

    yield factory
    for arm in made:
        # BaseManipulator.__del__ moves a connected arm to sleep: nothing to do here
        arm.is_connected = False
        pybullet.removeBody(arm.p_robot_id)


@pytest.fixture
def arms(arm_factory: Callable[..., SO100Hardware]) -> list[SO100Hardware]:
    return [arm_factory(LEFT_SERIAL), arm_factory(RIGHT_SERIAL)]


@pytest.fixture(autouse=True)
def hardware_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """The endpoints see a server with real arms, unless `only_simulation` is asked for."""
    monkeypatch.setattr(config, "ONLY_SIMULATION", False)


@pytest.fixture
def only_simulation(hardware_mode: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Phosphobot started with --only-simulation."""
    monkeypatch.setattr(config, "ONLY_SIMULATION", True)


def _never(what: str) -> Any:
    def never() -> None:
        raise AssertionError(f"the endpoint under test asked for {what}")

    return never


def client_for(rcm: RobotConnectionManager) -> TestClient:
    """A test client of the control and recording endpoints over this manager."""
    teleop_manager = TeleopManager(rcm=rcm)
    app = FastAPI()
    app.include_router(control.router)
    app.include_router(recording.router)
    app.dependency_overrides[get_rcm] = lambda: rcm
    app.dependency_overrides[get_teleop_manager] = lambda: teleop_manager
    # The real ones open the cameras
    app.dependency_overrides[get_all_cameras] = _never("the cameras")
    app.dependency_overrides[get_recorder] = lambda: object()
    return TestClient(app)


@pytest.fixture
def client(arms: list[SO100Hardware]) -> Iterator[TestClient]:
    with client_for(FakeRCM(arms)) as test_client:
        yield test_client
