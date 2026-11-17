"""
/move/leader/start names its arms by id, by serial, or by both (cross-checked),
and a pair that names no existing arm starts nothing.
"""

import threading
import time

import pytest

from phosphobot.endpoints import control
from phosphobot.leader_follower import LeaderFollowerThread

from .conftest import LEFT_SERIAL, RIGHT_SERIAL


def start(client, **pair):
    return client.post(
        "/move/leader/start",
        json={
            "robot_pairs": [pair],
            "invert_controls": False,
            "enable_gravity_compensation": False,
        },
    )


def stop_and_join(client):
    """Stop the control loop, if one was started, and wait for its thread."""
    client.post("/move/leader/stop")
    control.signal_leader_follower.stop()
    for thread in threading.enumerate():
        if isinstance(thread, LeaderFollowerThread):
            thread.join(timeout=20)
            assert not thread.is_alive()


@pytest.mark.parametrize(
    "pair,code",
    [
        ({"leader_id": 0, "follower_id": -1}, 400),
        ({"leader_id": -1, "follower_id": 1}, 400),
        ({"leader_id": 0, "follower_id": 2}, 400),
        ({"leader_id": None, "follower_id": 1}, 400),
        ({"leader_id": 0, "follower_id": None}, 400),
        ({"leader_id": 0, "follower_id": 1, "follower_serial": LEFT_SERIAL}, 409),
        ({"leader_id": 1, "leader_serial": LEFT_SERIAL, "follower_id": 0}, 409),
        ({"leader_id": 0, "follower_serial": "nope"}, 404),
    ],
)
def test_pair_that_names_no_arm_starts_nothing(client, arms, pair, code):
    try:
        r = start(client, **pair)
        assert r.status_code == code
        assert not control.signal_leader_follower.is_in_loop()
    finally:
        stop_and_join(client)
    assert all(a.motors_bus.calls == [] for a in arms)


@pytest.mark.parametrize(
    "pair",
    [
        {"leader_id": 0, "follower_id": 1},
        {"leader_serial": LEFT_SERIAL, "follower_serial": RIGHT_SERIAL},
        {"leader_id": 0, "leader_serial": LEFT_SERIAL, "follower_id": 1},
    ],
)
def test_valid_pair_starts_and_the_follower_follows(client, arms, pair):
    leader, follower = arms
    try:
        r = start(client, **pair)
        assert r.status_code == 200
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if ("write", "Goal_Position") in follower.motors_bus.calls:
                break
            time.sleep(0.05)
    finally:
        stop_and_join(client)
    assert ("write", "Goal_Position") in follower.motors_bus.calls
    # Both arms are released when the loop stops
    assert leader.motors_bus.regs["Torque_Enable"] == [0] * 6
    assert follower.motors_bus.regs["Torque_Enable"] == [0] * 6
