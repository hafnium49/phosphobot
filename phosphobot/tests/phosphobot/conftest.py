"""
Guard for every test under tests/phosphobot: no test can scan or open a real port.

The rig PC runs these tests next to a live phosphobot. RobotConnectionManager.robots
scans the serial ports and connects to whatever it finds, and AllCameras opens the
video devices, so each way out to hardware raises here instead.
"""

from typing import Any

import pytest
import serial
import serial.tools.list_ports

from phosphobot.camera import AllCameras
from phosphobot.hardware.motors.feetech import FeetechMotorsBus


def _refuse(what: str) -> Any:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(f"a test tried to reach real hardware: {what}")

    return refuse


@pytest.fixture(autouse=True)
def no_real_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        serial.tools.list_ports, "comports", _refuse("serial port scan")
    )
    monkeypatch.setattr(FeetechMotorsBus, "connect", _refuse("FeetechMotorsBus.connect"))
    # Every other bus (Dynamixel, the Feetech SDK's own port handler) opens its port here
    monkeypatch.setattr(serial.Serial, "open", _refuse("serial.Serial.open"))
    monkeypatch.setattr(AllCameras, "__init__", _refuse("AllCameras()"))
