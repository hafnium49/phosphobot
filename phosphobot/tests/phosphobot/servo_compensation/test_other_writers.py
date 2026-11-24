"""
Anything else that writes an arm's goal voids that arm's streams: what they knew
(the last request, its speed, the side the joints came from) is not what the servos
hold any more. The next compensated request starts a stream.
"""

import numpy as np
import pytest

from phosphobot.hardware import servo_compensation as sc

from .conftest import (
    DT,
    LEFT,
    OTHER_WRITERS,
    RIGHT,
    Q,
    compensator,
    goal,
    start_stream,
    units,
    write,
)


@pytest.mark.parametrize("name", list(OTHER_WRITERS))
def test_another_writer_of_the_goal_voids_the_arms_streams(
    client, arms, config_file, clock, no_waits, name
):
    left, arm = arms
    calibration = arm.config
    # The move endpoints do not move to the initial position first
    arm.initial_position, arm.initial_orientation_rad = np.zeros(3), np.zeros(3)
    start_stream(client, clock, arm=LEFT)
    last = start_stream(client, clock)
    state = arm.servo_compensation
    assert state.terms == "full" and state.requested_position == units(arm, last)
    assert state.streams["full"].pending

    OTHER_WRITERS[name](client, arm)

    assert state.terms is None and state.requested_position is None
    assert all(s._q is None and not s.pending for s in state.streams.values())
    # The other arm's stream is its own
    assert left.servo_compensation.terms == "full"
    assert left.servo_compensation.streams["full"].pending

    if name == "robot/disconnect":
        return
    # The next compensated request starts a stream: no speed, no direction
    arm.config, arm.is_connected = calibration, True
    clock.advance(DT)
    assert write(client, last).status_code == 200
    fresh = compensator().command(last, np.zeros(5), np.zeros(5))
    assert goal(arm) == units(arm, fresh)


def test_reads_leave_the_streams_alone(client, arms, config_file, clock):
    arm, mirror = arms[1], sc.Stream(compensator())
    arm.initial_position, arm.initial_orientation_rad = np.zeros(3), np.zeros(3)
    q = start_stream(client, clock)
    mirror.step(Q, clock.t - DT)
    mirror.step(q, clock.t)
    for path in (
        "/joints/read",
        "/joints/read/raw",
        "/torque/read",
        "/voltage/read",
        "/temperature/read",
        "/end-effector/read",
    ):
        assert client.post(path, params=RIGHT).status_code == 200, path
    assert arm.servo_compensation.terms == "full"
    q[1] -= 0.02
    clock.advance(DT)
    assert write(client, q).status_code == 200
    assert goal(arm) == units(arm, mirror.step(q, clock.t))
