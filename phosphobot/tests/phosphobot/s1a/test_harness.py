"""
The endpoint harness itself, and the behaviour a request with `robot_id` has today.
These pin what R6 (existing callers keep working) must keep.
"""

import pytest
import serial.tools.list_ports

from phosphobot.models import BaseRobotConfig


def test_no_test_can_scan_ports():
    with pytest.raises(AssertionError):
        serial.tools.list_ports.comports()


def test_no_test_can_write_a_calibration_file(arms):
    with pytest.raises(AssertionError):
        BaseRobotConfig.save_local(arms[0].config, serial_id="5A68011258")


def test_legacy_read_shape(client):
    r = client.post("/joints/read", params={"robot_id": 1}, json={"unit": "rad"})
    assert r.status_code == 200
    assert len(r.json()["angles"]) == 6 and r.json()["unit"] == "rad"


def test_legacy_write_and_toggle_reach_only_that_arm(client, arms):
    w = client.post(
        "/joints/write",
        params={"robot_id": 1},
        json={"angles": [0.1] * 6, "unit": "rad"},
    )
    t = client.post(
        "/torque/toggle", params={"robot_id": 1}, json={"torque_status": False}
    )
    assert w.status_code == 200 and t.status_code == 200
    assert t.json()["status"] == "ok"
    assert ("write", "Goal_Position") in arms[1].motors_bus.calls
    assert arms[1].motors_bus.regs["Torque_Enable"] == [0] * 6
    assert arms[0].motors_bus.calls == []
