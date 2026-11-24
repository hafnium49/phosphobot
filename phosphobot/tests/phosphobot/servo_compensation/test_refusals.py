"""
A request that asks for compensation and cannot have it is refused, and nothing is
written: there is no silent fallback to an uncompensated write.
"""

import json

import pytest

from phosphobot import compensated_write
from phosphobot.hardware import servo_compensation as sc

from .conftest import CONFIG, RIGHT, RIGHT_SERIAL, Q, goal, units, write

UNCOMPENSATED = {"angles": Q, "unit": "rad"}


def refused(client, arm, code, *words, **kwargs):
    r = write(client, kwargs.pop("angles", Q), **kwargs)
    assert r.status_code == code, r.text
    for word in words:
        assert word in r.json()["detail"], r.json()["detail"]
    assert arm.motors_bus.calls == []
    # The server is as it was: the same request without `compensate` is written
    r = client.post("/joints/write", params=RIGHT, json=UNCOMPENSATED)
    assert r.status_code == 200 and "compensation" not in r.json()
    assert goal(arm) == units(arm, Q)
    arm.motors_bus.calls.clear()


def test_without_the_variable_compensation_is_unavailable(client, arms):
    refused(client, arms[1], 501, "PHOSPHOBOT_SERVO_COMPENSATION is not set")
    refused(client, arms[1], 501, terms="static")


def test_a_file_that_cannot_be_read_or_has_another_schema(
    client, arms, monkeypatch, tmp_path
):
    other_schema = tmp_path / "schema2.json"
    other_schema.write_text(json.dumps({**json.loads(CONFIG.read_text()), "schema": 2}))
    not_json = tmp_path / "broken.json"
    not_json.write_text("{")
    for path, word in (
        (tmp_path / "missing.json", "missing.json"),
        (other_schema, "schema"),
        (not_json, "broken.json"),
        (tmp_path, str(tmp_path)),
    ):
        monkeypatch.setattr(compensated_write, "_config", None)
        monkeypatch.setenv(compensated_write.ENV_VAR, str(path))
        refused(client, arms[1], 500, word)


def test_the_file_is_loaded_once_at_the_first_request_that_asks(
    client, arms, config_file, monkeypatch
):
    loads = []
    real = sc.Compensator.from_config

    def counting(path, serial):
        loads.append(serial)
        return real(path, serial)

    monkeypatch.setattr(sc.Compensator, "from_config", staticmethod(counting))
    client.post("/joints/write", params=RIGHT, json=UNCOMPENSATED)
    client.post("/joints/read", params=RIGHT)
    assert loads == [] and compensated_write._config is None
    for _ in range(3):
        assert write(client, Q).status_code == 200
        assert write(client, Q, arm={"robot_id": 0}).status_code == 200
    assert sorted(loads) == sorted(["5A68009540", "5A68011258"])
    # A file that failed is not read again either: the server is restarted for it
    monkeypatch.setattr(compensated_write, "_config", None)
    monkeypatch.setenv(compensated_write.ENV_VAR, "/nonexistent/comp.json")
    assert write(client, Q).status_code == 500
    monkeypatch.setenv(compensated_write.ENV_VAR, str(config_file))
    assert write(client, Q).status_code == 500


def test_an_arm_that_is_not_in_the_config(client, arms, config_file):
    arms[1].SERIAL_ID = "5A68011529"
    r = write(client, Q, arm={"robot_id": 1})
    assert r.status_code == 409 and arms[1].motors_bus.calls == []
    assert "5A68011529 is not in" in r.json()["detail"]
    assert RIGHT_SERIAL in r.json()["detail"]


@pytest.mark.parametrize(
    "change,word",
    [
        (lambda c: c.servos_offsets_signs.__setitem__(2, -1.0), "servos_offsets_signs"),
        (lambda c: c.servos_offsets.__setitem__(4, 2050.0), "servos_offsets "),
        (lambda c: setattr(c, "servos_offsets", [2048.0] * 5), "servos_offsets "),
    ],
)
def test_a_calibration_that_is_not_the_configs(client, arms, config_file, change, word):
    change(arms[1].config)
    r = write(client, Q)
    assert r.status_code == 409 and arms[1].motors_bus.calls == []
    assert "calibration" in r.json()["detail"] and word in r.json()["detail"]


def test_an_arm_without_calibration(client, arms, config_file):
    arms[1].config = None
    r = write(client, Q)
    assert r.status_code == 409 and "no calibration" in r.json()["detail"]
    assert arms[1].motors_bus.calls == []


def test_the_request_must_be_six_angles_in_radians(client, arms, config_file):
    arm = arms[1]
    refused(client, arm, 400, "rad", unit="degrees")
    refused(client, arm, 400, "rad", unit="motor_units")
    refused(client, arm, 400, "6", angles=Q[:5])
    refused(client, arm, 400, "6", angles=Q + [0.0])
    refused(client, arm, 400, "joints_ids", angles=Q, joints_ids=[1, 2, 3, 4, 5, 6])
    refused(client, arm, 400, angles=[0.2, -0.6, 4.0, 0.4, -0.3, 0.05])
    refused(client, arm, 422, terms="half")
    assert arm.servo_compensation is None or arm.servo_compensation.terms is None


def test_an_arm_off_the_bus_is_not_compensated_in_simulation(
    client, arms, config_file, only_simulation
):
    arms[1].is_connected = False
    r = write(client, Q)
    assert r.status_code == 503 and "not on the bus" in r.json()["detail"]
    assert arms[1].motors_bus.calls == []


def test_a_failed_bus_write_is_502_and_leaves_no_stream(client, arms, config_file):
    arm = arms[1]
    assert write(client, Q).status_code == 200
    arm.motors_bus.fail = {"write:Goal_Position"}
    r = write(client, Q)
    assert r.status_code == 502 and "bus write failed" in r.json()["detail"]
    state = arm.servo_compensation
    assert state.terms is None and state.requested_position is None
    assert all(stream._q is None for stream in state.streams.values())
