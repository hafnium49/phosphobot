"""
POST /joints/read/raw says what was asked for: `goal_position` is the register (the
compensated command), `requested_position` the last compensated request in motor
units, `compensation` its terms. Both are null when the arm's last goal write was
not a compensated one.
"""

import pytest

from .conftest import LEFT, RIGHT, Q, goal, start_stream, units, write
from .test_default_path import BASE_UNITS_RAD


def raw(client, arm=RIGHT):
    r = client.post("/joints/read/raw", params=arm)
    assert r.status_code == 200, r.text
    return r.json()


def test_the_raw_read_reports_the_request_next_to_the_register(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    b = raw(client)
    assert (b["requested_position"], b["compensation"]) == (None, None)

    assert write(client, Q).status_code == 200
    b = raw(client)
    # The request, converted as an uncompensated write of it would be
    assert b["requested_position"] == BASE_UNITS_RAD == units(arm, Q)
    assert b["compensation"] == "full"
    assert b["goal_position"] == goal(arm) != b["requested_position"]
    # Six ticks: the gripper is as requested
    assert b["goal_position"][5] == b["requested_position"][5]

    assert write(client, Q, terms="static").status_code == 200
    assert raw(client)["compensation"] == "static"
    # The other arm was not written
    b = raw(client, LEFT)
    assert (b["requested_position"], b["compensation"]) == (None, None)


def test_the_request_stays_through_the_rest_command(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    last = start_stream(client, clock)
    moving = raw(client)
    timers[-1].fire()
    b = raw(client)
    assert b["requested_position"] == moving["requested_position"] == units(arm, last)
    assert b["compensation"] == "full" and b["goal_position"] != moving["goal_position"]


@pytest.mark.parametrize(
    "other",
    [
        lambda client, arm: client.post(
            "/joints/write", params=RIGHT, json={"angles": Q, "unit": "rad"}
        ),
        lambda client, arm: client.post(
            "/torque/toggle", params=RIGHT, json={"torque_status": False}
        ),
        lambda client, arm: client.post(
            "/torque/toggle", params=RIGHT, json={"torque_status": True}
        ),
        lambda client, arm: arm.control_gripper(1.0),
        lambda client, arm: arm.motors_bus.fail.add("write:Goal_Position")
        or write(client, Q)
        or arm.motors_bus.fail.clear(),
    ],
)
def test_after_any_other_goal_write_the_request_is_null(
    client, arms, config_file, clock, other
):
    arm = arms[1]
    start_stream(client, clock)
    assert raw(client)["compensation"] == "full"
    other(client, arm)
    arm.motors_bus.fail.clear()
    b = raw(client)
    assert (b["requested_position"], b["compensation"]) == (None, None)
    assert b["goal_position"] == goal(arm)
