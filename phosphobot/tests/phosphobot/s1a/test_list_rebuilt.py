"""
The list of robots can be rebuilt between the moment a request names its arm and
the moment the arm is moved: a USB drop or re-attach, found by the next port scan.
`robot_id` is a position in that list, so nothing may look an id up again after
the arm was resolved. The request acts on the robot it resolved, or on nothing.
"""

import pytest

from .conftest import LEFT_SERIAL, RIGHT_SERIAL, RescanRCM, client_for

TELEOP = {"x": 0, "y": 0, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 1}


def no_bus_call(*arms):
    # A robot that left the list is disconnected by the manager: not a bus operation
    return all(set(a.motors_bus.calls) <= {("disconnect", "")} for a in arms)


@pytest.mark.parametrize(
    "params", [{"robot_id": 0, "serial": LEFT_SERIAL}, {"serial": LEFT_SERIAL}]
)
@pytest.mark.parametrize("path,body", [("/move/init", None), ("/move/teleop", TELEOP)])
def test_dropped_arm_request_does_not_reach_the_arm_that_took_its_place(
    arms, arm_factory, params, path, body
):
    # The list was [LEFT, RIGHT]. LEFT dropped off USB: the next scan gives [RIGHT]
    new_right = arm_factory(RIGHT_SERIAL)
    with client_for(RescanRCM(old=arms, new=[new_right])) as client:
        r = client.post(path, params=params, json=body)
    assert no_bus_call(new_right, *arms)
    assert new_right.initial_position is None
    if path == "/move/init":
        assert r.status_code == 409 and LEFT_SERIAL in r.json()["detail"]


@pytest.mark.parametrize(
    "params", [{"robot_id": 1, "serial": RIGHT_SERIAL}, {"serial": RIGHT_SERIAL}]
)
@pytest.mark.parametrize("path,body", [("/move/init", None), ("/move/teleop", TELEOP)])
def test_list_that_comes_back_in_the_other_order_moves_no_arm(
    arms, arm_factory, params, path, body
):
    # Both arms were re-attached and came back as [RIGHT, LEFT]
    new_right, new_left = arm_factory(RIGHT_SERIAL), arm_factory(LEFT_SERIAL)
    with client_for(RescanRCM(old=arms, new=[new_right, new_left])) as client:
        r = client.post(path, params=params, json=body)
    assert no_bus_call(new_right, new_left, *arms)
    if path == "/move/init":
        assert r.status_code == 409


def test_the_request_repeated_after_the_refusal_reaches_the_named_arm(
    arms, arm_factory
):
    new_right, new_left = arm_factory(RIGHT_SERIAL), arm_factory(LEFT_SERIAL)
    with client_for(RescanRCM(old=arms, new=[new_right, new_left])) as client:
        assert client.post("/move/init", params={"serial": RIGHT_SERIAL}).status_code == 409
        r = client.post("/move/init", params={"serial": RIGHT_SERIAL})
    assert r.status_code == 200
    assert ("write", "Goal_Position") in new_right.motors_bus.calls
    assert new_right.initial_position is not None and no_bus_call(new_left)


def test_disconnect_removes_the_resolved_robot_not_a_position(arms):
    with client_for(RescanRCM(old=arms, new=[])) as client:
        r = client.post("/robot/disconnect", params={"serial": RIGHT_SERIAL})
    assert r.status_code == 200
    assert ("disconnect", "") in arms[1].motors_bus.calls
    assert arms[0].motors_bus.calls == []
