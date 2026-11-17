"""
R2, R5: an arm is named by `robot_id`, by `serial`, or by both (cross-checked).
A moving or setting endpoint refuses a request that names no arm.
"""

import pytest

W = {"angles": [0.1] * 6, "unit": "rad"}
MOVERS = [
    ("/move/init", None),
    ("/move/teleop", None),
    ("/move/absolute", {"x": 0, "y": 0, "z": 0}),
    ("/move/relative", {"x": 1}),
    ("/move/hello", None),
    ("/move/sleep", None),
    ("/temperature/write", {"maximum_temperature": [70] * 6}),
    ("/torque/toggle", {"torque_status": False}),
    ("/joints/write", W),
    ("/calibrate", None),
    ("/gravity/start", None),
    ("/robot/disconnect", None),
]


@pytest.mark.parametrize("path,body", MOVERS)
def test_mover_without_arm_is_refused(client, arms, path, body):
    r = client.post(path, json=body)
    assert r.status_code == 422 and "robot_id or serial" in str(r.json()["detail"])
    assert all(a.motors_bus.calls == [] for a in arms)


def test_serial_addresses_the_arm(client, arms):
    r = client.post("/joints/write", params={"serial": "5A68009540"}, json=W)
    assert r.status_code == 200
    assert arms[0].motors_bus.calls == [] and arms[1].motors_bus.calls != []


def test_stale_id_with_serial_is_refused_not_obeyed(client, arms):
    r = client.post(
        "/joints/write", params={"robot_id": 0, "serial": "5A68009540"}, json=W
    )
    assert r.status_code == 409 and all(a.motors_bus.calls == [] for a in arms)
    assert r.json()["detail"] == "robot_id 0 is 5A68011258, not 5A68009540"


def test_id_and_serial_that_agree_are_obeyed(client, arms):
    r = client.post(
        "/joints/write", params={"robot_id": 1, "serial": "5A68009540"}, json=W
    )
    assert r.status_code == 200
    assert arms[0].motors_bus.calls == [] and arms[1].motors_bus.calls != []


def test_bad_selectors(client, arms):
    off = {"torque_status": False}

    def toggle(**params):
        return client.post("/torque/toggle", params=params, json=off).status_code

    assert toggle(robot_id=-1) == 400
    assert toggle(robot_id=2) == 400
    assert toggle(serial="nope") == 404
    arms[0].SERIAL_ID = arms[1].SERIAL_ID = "no_serial"
    assert toggle(serial="no_serial") == 400
    arms[0].SERIAL_ID = arms[1].SERIAL_ID = "5A68009540"
    assert toggle(serial="5A68009540") == 400
    assert all(a.motors_bus.regs["Torque_Enable"] == [1] * 6 for a in arms)


def test_read_without_arm_still_answers_from_robot_0(client):
    assert client.post("/joints/read").status_code == 200


def test_read_endpoints_take_a_serial(client, arms):
    r = client.post("/robot/config", params={"serial": "5A68009540"})
    assert r.status_code == 200 and r.json()["robot_id"] == 1
    assert client.post("/joints/read", params={"serial": "nope"}).status_code == 404
