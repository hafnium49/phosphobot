"""
Guard for every test under tests/phosphobot: no test can scan or open a real port.

The rig PC runs these tests next to a live phosphobot. RobotConnectionManager.robots
scans the serial ports and connects to whatever it finds, and AllCameras opens the
video devices, so each way out to hardware raises here instead. So does saving a
calibration: ~/phosphobot/calibration holds the rig's own files, keyed by serial.
So does a socket connection to a port of the rig's services (the live phosphobot
on 8080 and the bench shims on 5570 and 5571), whatever the client library.
"""

import socket
from typing import Any

import pytest
import serial
import serial.tools.list_ports

from phosphobot.camera import AllCameras
from phosphobot.hardware.motors.feetech import FeetechMotorsBus
from phosphobot.models import BaseRobotConfig


def _refuse(what: str) -> Any:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(f"a test tried to reach real hardware: {what}")

    return refuse


RIG_PORTS = {8080, 5570, 5571}


def _guard_connect(real_connect: Any) -> Any:
    def guarded_connect(sock: socket.socket, address: Any, *args: Any) -> Any:
        if isinstance(address, tuple) and len(address) >= 2 and address[1] in RIG_PORTS:
            raise AssertionError(
                f"a test tried to reach real hardware: connection to {address}"
            )
        return real_connect(sock, address, *args)

    return guarded_connect


@pytest.fixture(autouse=True)
def no_real_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    # requests, httpx, websockets and asyncio all connect through these two
    monkeypatch.setattr(socket.socket, "connect", _guard_connect(socket.socket.connect))
    monkeypatch.setattr(
        socket.socket, "connect_ex", _guard_connect(socket.socket.connect_ex)
    )
    monkeypatch.setattr(
        serial.tools.list_ports, "comports", _refuse("serial port scan")
    )
    monkeypatch.setattr(FeetechMotorsBus, "connect", _refuse("FeetechMotorsBus.connect"))
    # Every other bus (Dynamixel, the Feetech SDK's own port handler) opens its port here
    monkeypatch.setattr(serial.Serial, "open", _refuse("serial.Serial.open"))
    monkeypatch.setattr(AllCameras, "__init__", _refuse("AllCameras()"))
    monkeypatch.setattr(
        BaseRobotConfig, "save_local", _refuse("write of a calibration file")
    )
