"""
R4: a write or a torque toggle answers 200 only when the bus operation was done.
"""

import numpy as np
import pytest

W = {"angles": [0.1] * 6, "unit": "rad"}
R1 = {"robot_id": 1}
ON = {"torque_status": True}


def test_good_write_names_the_arm_and_a_failed_one_is_502(client, arms):
    b = client.post("/joints/write", params=R1, json=W).json()
    assert (b["status"], b["robot_id"], b["serial"], b["bus_write"]) == (
        "ok",
        1,
        "5A68009540",
        True,
    )
    arms[1].motors_bus.fail = {"write:Goal_Position"}
    r = client.post("/joints/write", params=R1, json=W)
    assert r.status_code == 502 and "bus write failed" in r.json()["detail"]


def test_write_to_dropped_arm_is_503(client, arms):
    arms[1].is_connected = False
    r = client.post("/joints/write", params=R1, json=W)
    assert r.status_code == 503 and arms[1].motors_bus.calls == []


def test_joints_ids_write_is_refused(client, arms):
    r = client.post(
        "/joints/write",
        params=R1,
        json={"angles": [0.1], "unit": "rad", "joints_ids": [1]},
    )
    assert r.status_code == 400 and arms[1].motors_bus.calls == []


def test_degrees_are_degrees(client, arms):
    r = client.post(
        "/joints/write",
        params=R1,
        json={"angles": [90, 0, 0, 0, 0, 0], "unit": "degrees"},
    )
    want = arms[1]._radians_vec_to_motor_units(np.array([np.pi / 2, 0, 0, 0, 0, 0]))
    assert r.status_code == 200
    assert arms[1].motors_bus.regs["Goal_Position"] == list(want)


def test_short_write_reports_each_servo_write(client, arms):
    short = {"angles": [0.1, 0.1], "unit": "rad"}
    r = client.post("/joints/write", params=R1, json=short)
    assert r.status_code == 200 and r.json()["bus_write"] is True
    assert arms[1].motors_bus.calls.count(("write", "Goal_Position")) == 2
    arms[1].motors_bus.fail = {"write:Goal_Position"}
    assert client.post("/joints/write", params=R1, json=short).status_code == 502


def test_write_methods_say_whether_the_bus_write_was_issued(arms):
    arm = arms[1]
    assert arm.write_group_motor_position(np.array([2048] * 6)) is True
    assert arm.write_motor_position(servo_id=1, units=2048) is True
    assert arm.set_motors_positions(np.zeros(6), enable_gripper=True) is True
    assert arm.write_joint_positions([0.0] * 6, unit="rad") is True
    arm.motors_bus.fail = {"write:Goal_Position"}
    assert arm.write_group_motor_position(np.array([2048] * 6)) is False
    assert arm.write_motor_position(servo_id=1, units=2048) is False
    assert arm.set_motors_positions(np.zeros(6), enable_gripper=True) is False
    assert arm.write_joint_positions([0.0] * 6, unit="rad") is False
    arm.motors_bus.fail = set()
    arm.is_connected = False
    assert arm.write_group_motor_position(np.array([2048] * 6)) is False
    assert arm.write_motor_position(servo_id=1, units=2048) is False
    assert arm.set_motors_positions(np.zeros(6), enable_gripper=True) is False


@pytest.mark.parametrize(
    "setup,code",
    [
        (lambda a: setattr(a, "is_connected", False), 503),
        (lambda a: a.motors_bus.fail.add("write:Torque_Enable"), 502),
        (lambda a: a.motors_bus.ignore.add("Torque_Enable"), 502),
        (lambda a: a.motors_bus.fail.add("write:P_Coefficient"), 502),
        (lambda a: a.motors_bus.fail.add("read:Torque_Enable"), 502),
    ],
)
def test_toggle_failures_are_not_200(client, arms, setup, code):
    arms[1].motors_bus.regs["Torque_Enable"] = [0] * 6
    setup(arms[1])
    assert client.post("/torque/toggle", params=R1, json=ON).status_code == code


def test_toggle_off_that_did_not_take_is_502(client, arms):
    arms[1].motors_bus.ignore.add("Torque_Enable")
    r = client.post("/torque/toggle", params=R1, json={"torque_status": False})
    assert r.status_code == 502 and "Torque_Enable read back" in r.json()["detail"]


def test_toggle_reports_the_state_it_read_back(client):
    b = client.post("/torque/toggle", params=R1, json={"torque_status": False}).json()
    assert b["torque_enabled"] == [False] * 6 and b["serial"] == "5A68009540"
    assert b["robot_id"] == 1 and b["bus_write"] is True
    b = client.post("/torque/toggle", params=R1, json=ON).json()
    assert b["status"] == "ok" and b["torque_enabled"] == [True] * 6


def test_enable_writes_the_gains_of_the_calibration(client, arms):
    arms[1].motors_bus.regs["Torque_Enable"] = [0] * 6
    assert client.post("/torque/toggle", params=R1, json=ON).status_code == 200
    gains = arms[1].config.pid_gains
    assert arms[1].motors_bus.regs["P_Coefficient"] == [int(g.p_gain) for g in gains]
    assert arms[1].motors_bus.regs["D_Coefficient"] == [int(g.d_gain) for g in gains]


def test_only_simulation_write_is_still_200(client, arms, only_simulation):
    arms[1].is_connected = False
    r = client.post("/joints/write", params=R1, json=W)
    assert r.status_code == 200 and r.json()["bus_write"] is False
    r = client.post("/torque/toggle", params=R1, json=ON)
    assert r.status_code == 200 and r.json()["bus_write"] is False


def test_write_of_no_angles_does_not_claim_a_bus_write(client, arms):
    r = client.post("/joints/write", params=R1, json={"angles": [], "unit": "rad"})
    assert r.status_code == 200 and r.json()["bus_write"] is None
    assert arms[1].motors_bus.calls == []
