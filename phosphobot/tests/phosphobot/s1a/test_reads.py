"""
R1, R3: a read says which arm answered, from where and how old; a dropped arm is
not answered from the simulation; the raw read returns the servos' own ticks.
"""

import pytest

from phosphobot.hardware import SO100Hardware
from phosphobot.hardware.motors import feetech
from phosphobot.hardware.motors.feetech import FeetechMotorsBus

from .conftest import FakeRCM

R1 = {"robot_id": 1}


def test_read_says_which_arm_from_where_and_how_old(client):
    b = client.post("/joints/read", params=R1, json={"unit": "rad"}).json()
    assert (b["robot_id"], b["serial"], b["source"], b["bus_connected"]) == (
        1,
        "5A68009540",
        "hardware",
        True,
    )
    assert 0 <= b["read_age_ms"] < 1000 and b["read_unix_s"] > 0
    assert b["torque_enabled"] == [True] * 6 and 0 <= b["torque_age_ms"] < 1000
    assert len(b["angles"]) == 6


def test_failed_bus_read_is_502_and_a_read_while_moving_is_labelled(client, arms):
    arms[1].motors_bus.fail = {"read:Present_Position"}
    assert client.post("/joints/read", params=R1).status_code == 502
    arms[1].is_moving = True
    b = client.post("/joints/read", params=R1).json()
    assert b["source"] == "simulation" and b["read_age_ms"] is None


def test_dropped_arm_read_is_503_never_simulation(client, arms):
    arms[1].is_connected = False
    r = client.post("/joints/read", params=R1)
    assert r.status_code == 503 and "5A68009540 is not on the bus" in r.json()["detail"]
    b = client.post(
        "/joints/read", params=R1, json={"unit": "rad", "source": "sim"}
    ).json()
    assert b["source"] == "simulation" and b["read_age_ms"] is None
    assert b["bus_connected"] is False and b["torque_enabled"] is None


def test_only_simulation_read_still_answers(client, arms, only_simulation):
    arms[1].is_connected = False
    r = client.post("/joints/read", params=R1)
    assert r.status_code == 200 and r.json()["source"] == "simulation"


def test_torque_is_read_once_per_quarter_second_and_again_after_a_toggle(client, arms):
    client.post("/joints/read", params=R1)
    client.post("/joints/read", params=R1)
    assert arms[1].motors_bus.calls.count(("read", "Torque_Enable")) == 1
    client.post("/torque/toggle", params=R1, json={"torque_status": False})
    b = client.post("/joints/read", params=R1).json()
    assert b["torque_enabled"] == [False] * 6


def test_torque_cache_expires_and_a_failed_torque_read_is_null(arms):
    arm = arms[1]
    assert arm.read_torque_enabled() == ([True] * 6, 0.0)
    values, age_s = arm.read_torque_enabled()
    assert values == [True] * 6 and age_s is not None and age_s >= 0
    assert arm.motors_bus.calls.count(("read", "Torque_Enable")) == 1
    arm.read_torque_enabled(max_age_s=0)
    assert arm.motors_bus.calls.count(("read", "Torque_Enable")) == 2
    arm.motors_bus.fail = {"read:Torque_Enable"}
    assert arm.read_torque_enabled(max_age_s=0) == (None, None)
    arm.is_connected = False
    assert arm.read_torque_enabled() == (None, None)


def test_disconnect_drops_the_torque_cache(arms):
    arm = arms[1]
    arm.read_torque_enabled()
    arm.disconnect()
    arm.is_connected = True
    arm.motors_bus.regs["Torque_Enable"] = [0] * 6
    assert arm.read_torque_enabled()[0] == [False] * 6


@pytest.mark.asyncio
async def test_status_rows_name_their_arm(arms):
    arms[0].is_connected = False
    rows = await FakeRCM(arms).status()
    assert (
        rows[1].robot_id,
        rows[1].serial,
        rows[1].bus_connected,
        rows[1].torque_enabled,
    ) == (1, "5A68009540", True, [True] * 6)
    assert rows[1].readback_source == "hardware" and rows[1].status_unix_s > 0
    assert (rows[0].bus_connected, rows[0].readback_source, rows[0].torque_enabled) == (
        False,
        "simulation",
        None,
    )
    assert rows[0].robot_id == 0 and rows[1].device_name == "5A68009540"


def test_server_status_says_the_api_is_truthful():
    from phosphobot.models import ServerStatus

    status = ServerStatus(status="ok", name="x", server_ip="127.0.0.1", server_port=80)
    assert status.truthful_api == 1


def test_raw_read_is_ticks_from_the_bus(client, arms):
    bus = arms[1].motors_bus
    bus.regs["Present_Position"], bus.regs["Goal_Position"] = [1, 2, 3, 4, 5, 6], [7] * 6
    r = client.post("/joints/read/raw", params={"serial": "5A68009540"})
    b = r.json()
    assert r.status_code == 200 and (b["robot_id"], b["serial"]) == (1, "5A68009540")
    assert b["present_position"] == [1, 2, 3, 4, 5, 6] and b["goal_position"] == [7] * 6
    assert b["torque_enabled"] == [True] * 6 and b["servo_ids"] == [1, 2, 3, 4, 5, 6]
    assert 0 <= b["read_age_ms"] < 1000 and b["read_unix_s"] > 0
    # the unwrapping path is not used
    assert ("read", "Present_Position") not in bus.calls
    assert client.post("/joints/read/raw").status_code == 422
    bus.fail = {"read:Goal_Position"}
    assert client.post("/joints/read/raw", params=R1).status_code == 502
    arms[1].is_connected = False
    assert client.post("/joints/read/raw", params=R1).status_code == 503


def test_raw_read_is_never_simulation(client, arms, only_simulation):
    arms[1].is_connected = False
    assert client.post("/joints/read/raw", params=R1).status_code == 503


def fake_group_returning(value):
    class FakeGroupSyncRead:
        def __init__(self, *args):
            pass

        def addParam(self, idx):
            return True

        def txRxPacket(self):
            return feetech.scs.COMM_SUCCESS

        def getData(self, idx, addr, nb_bytes):
            return value

    return FakeGroupSyncRead


def test_by_id_bus_read_does_not_unwrap(monkeypatch):
    """Pins what the raw read relies on: the by-id read returns the words as read."""
    bus = FeetechMotorsBus(port="none", motors=SO100Hardware.motors)
    monkeypatch.setattr(feetech.scs, "GroupSyncRead", fake_group_returning(1))
    bus.track_positions = {
        "Present_Position": {
            "prev": [4095] * 6,
            "below_zero": [False] * 6,
            "above_max": [False] * 6,
        }
    }
    words = bus._perform_read_with_motor_ids(
        ["sts3215"] * 6, [1, 2, 3, 4, 5, 6], "Present_Position"
    )
    assert words == [1] * 6
    assert bus.track_positions["Present_Position"]["prev"] == [4095] * 6


def test_torque_read_is_per_servo_and_fails_loudly(client, arms):
    arms[1].motors_bus.regs["Present_Current"] = [11, 12, 13, 14, 15, 16]
    r = client.post("/torque/read", params=R1)
    b = r.json()
    assert r.status_code == 200 and b["current_torque"] == [11, 12, 13, 14, 15, 16]
    assert (b["robot_id"], b["serial"], b["source"]) == (1, "5A68009540", "hardware")
    arms[1].motors_bus.fail = {"read:Present_Current"}
    assert client.post("/torque/read", params=R1).status_code == 502
    arms[1].is_connected = False
    assert client.post("/torque/read", params=R1).status_code == 503


def test_current_torque_is_none_for_a_servo_whose_read_failed(arms):
    arm = arms[1]
    arm.motors_bus.regs["Present_Current"] = [11, 12, 13, 14, 15, 16]
    assert list(arm.current_torque()) == [11, 12, 13, 14, 15, 16]
    arm.read_motor_torque = lambda servo_id: None if servo_id == 3 else 7.0
    assert list(arm.current_torque()) == [7.0, 7.0, None, 7.0, 7.0, 7.0]


def test_only_simulation_torque_read_still_answers(client, arms, only_simulation):
    arms[1].is_connected = False
    r = client.post("/torque/read", params=R1)
    assert r.status_code == 200 and r.json()["source"] == "simulation"
    assert len(r.json()["current_torque"]) == 6


def test_read_of_single_joints_fails_loudly_too(client, arms):
    body = {"unit": "motor_units", "joints_ids": [1, 2]}
    arms[1].motors_bus.regs["Present_Position"] = [100, 200, 300, 400, 500, 600]
    r = client.post("/joints/read", params=R1, json=body)
    assert r.status_code == 200 and r.json()["angles"] == [100, 200]
    assert r.json()["source"] == "hardware"
    arms[1].motors_bus.fail = {"read:Present_Position"}
    assert client.post("/joints/read", params=R1, json=body).status_code == 502


def test_failed_read_of_one_servo_is_nan_not_zero(arms):
    import numpy as np

    arm = arms[1]
    arm.read_motor_position = lambda servo_id, **kwargs: None if servo_id == 2 else 7
    positions = arm.read_joints_position(unit="motor_units", joints_ids=[1, 2, 3])
    assert positions[0] == 7 and np.isnan(positions[1]) and positions[2] == 7


def test_read_age_is_taken_when_the_response_is_built(client, arms):
    import time

    bus = arms[1].motors_bus
    real_read = bus.read

    def slow_torque_read(data_name, motor_names=None):
        if data_name == "Torque_Enable":
            time.sleep(0.2)
        return real_read(data_name, motor_names)

    bus.read = slow_torque_read
    b = client.post("/joints/read", params=R1).json()
    # The positions were read before the torque: they are that much older
    assert b["read_age_ms"] >= 190
    assert abs((time.time() - b["read_unix_s"]) * 1000 - b["read_age_ms"]) < 100


def test_other_reads_name_the_arm_that_answered(client, arms):
    for path in ("/voltage/read", "/temperature/read"):
        b = client.post(path, params={"serial": "5A68009540"}).json()
        assert (b["robot_id"], b["serial"]) == (1, "5A68009540"), path
    b = client.post("/voltage/read").json()
    assert (b["robot_id"], b["serial"]) == (0, "5A68011258")
    assert b["current_voltage"] == [12.0] * 6
    b = client.post(
        "/end-effector/read", params=R1, json={"only_gripper": True, "sync": False}
    ).json()
    assert (b["robot_id"], b["serial"]) == (1, "5A68009540")
    arms[1].initial_position = arms[1].initial_orientation_rad = [0.0, 0.0, 0.0]
    b = client.post("/end-effector/read", params=R1).json()
    assert (b["robot_id"], b["serial"]) == (1, "5A68009540") and b["x"] is not None
