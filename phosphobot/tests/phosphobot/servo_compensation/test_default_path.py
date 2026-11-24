"""
Without `compensate`, POST /joints/write does what it did before the servo
compensation existed. The motor units and the response bytes below were taken from
the base commit (eae3154d) with these same requests, before any other change of
this work; they hold whether or not a compensation config is loaded.
"""

import socket

import pytest

from .conftest import CONFIG

R1 = {"robot_id": 1}
Q = [0.2, -0.6, 0.9, 0.4, -0.3, 0.05]
BASE_RESPONSE = b'{"status":"ok","message":null,"robot_id":1,"serial":"5A68009540","bus_write":true}'
BASE_UNITS_RAD = [1917, 1656, 2634, 2308, 1852, 2080]
BASE_UNITS_DEGREES = [1934, 1820, 2389, 2503, 1479, 2730]


def test_the_guard_against_the_rig_ports_is_in_place_here_too():
    assert socket.socket.connect.__name__ == "guarded_connect"
    for port in (8080, 5570, 5571):
        with pytest.raises(AssertionError):
            socket.create_connection(("127.0.0.1", port), timeout=1)


@pytest.mark.parametrize("config_file", [None, str(CONFIG), "/nonexistent/comp.json"])
def test_a_write_without_compensate_is_the_base_write(
    client, arms, monkeypatch, config_file
):
    if config_file is None:
        monkeypatch.delenv("PHOSPHOBOT_SERVO_COMPENSATION", raising=False)
    else:
        monkeypatch.setenv("PHOSPHOBOT_SERVO_COMPENSATION", config_file)
    bus = arms[1].motors_bus

    r = client.post("/joints/write", params=R1, json={"angles": Q, "unit": "rad"})
    assert (r.status_code, r.content) == (200, BASE_RESPONSE)
    assert bus.regs["Goal_Position"] == BASE_UNITS_RAD
    assert bus.calls == [("write", "Goal_Position")]

    r = client.post(
        "/joints/write",
        params=R1,
        json={"angles": [10, -20, 30, 40, -50, 60], "unit": "degrees"},
    )
    assert (r.status_code, r.content) == (200, BASE_RESPONSE)
    assert bus.regs["Goal_Position"] == BASE_UNITS_DEGREES
    assert bus.calls == [("write", "Goal_Position")] * 2
    assert arms[0].motors_bus.calls == []
