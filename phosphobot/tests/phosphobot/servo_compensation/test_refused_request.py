"""
A compensated request that is refused before anything reaches the bus changes
nothing: the stream is as it was after the last accepted request, and the rest
command of that request still comes. (A refused request used to cancel the pending
rest command and never replace it: the servo kept the command with the speed lead.)
"""

import numpy as np
import pytest

from phosphobot import compensated_write
from phosphobot.hardware import servo_compensation as sc

from .conftest import (
    DQ,
    DT,
    RIGHT,
    Q,
    command_with_lead,
    compensator,
    goal,
    goal_writes,
    lags,
    lead_of_a_line,
    line,
    speed_ticks,
    start_stream,
    units,
    write,
)

STREAM_STATE = ("_q", "_t", "_dir", "_intervals", "_lead", "pending")


def live(timers):
    return [timer for timer in timers if not timer.cancelled]


def state_of(stream):
    return {name: np.array(getattr(stream, name), dtype=float).tolist() for name in STREAM_STATE}


def rest_units(arm, request):
    return units(arm, compensator().command(request, np.zeros(5), np.zeros(5), sc.TERMS))


def raw(client):
    b = client.post("/joints/read/raw", params=RIGHT).json()
    return b["requested_position"], b["compensation"]


def test_the_snapshot_covers_the_whole_state_of_a_stream():
    """The server saves and restores these attributes; a runtime with more must be looked at."""
    assert set(compensated_write._STREAM_STATE) == set(STREAM_STATE)
    assert set(vars(sc.Stream(compensator()))) == {"comp", "terms", *STREAM_STATE}


def test_a_request_out_of_range_leaves_the_pending_rest_command(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    last = start_stream(client, clock)  # 0.3 rad/s on two joints
    moving, state = goal(arm), arm.servo_compensation
    stream = state.streams["full"]
    before = state_of(stream)
    (timer,) = live(timers)

    clock.advance(DT)
    bad = list(last)
    bad[2] = 4.0
    r = write(client, bad)
    assert r.status_code == 400 and "request" in r.json()["detail"]
    assert goal_writes(arm) == 2 and goal(arm) == moving
    # Nothing changed: the timer, the stream, what the raw read reports
    assert live(timers) == [timer] and len(timers) == 1
    assert state_of(stream) == before and state.streams == {"full": stream}
    assert raw(client) == (units(arm, last), "full")

    # The rest command of the last accepted request still comes
    clock.advance(timer.delay_s)
    timer.fire()
    assert goal_writes(arm) == 3 and goal(arm) == rest_units(arm, last) != moving
    assert raw(client) == (units(arm, last), "full")


def test_a_command_out_of_range_for_a_request_in_range_does_the_same(
    client, arms, config_file, clock, timers
):
    """
    The wrist roll towards +pi at 0.3 rad/s: each request leaves 13 ticks less room
    to pi and its command leads by 4 ticks more (runtime version 5). The request
    stays inside -pi..pi; at the sixth, its command does not.
    """
    arm, comp = arms[1], compensator()
    roll = [0.0, 0.0, 0.0, 0.0, 0.02, 0.0]
    v = speed_ticks(comp, roll)
    side = np.tanh(v / sc.V0)

    def added(q, k):
        """What the model adds to the wrist roll at the k-th moving request, ticks."""
        return -comp.error_ticks(q, lead_of_a_line(comp, roll, k) / lags(comp), side)[4]

    start = list(Q)
    start[4] = 3.00
    last = line(client, clock, 5, dq=roll, start=start)
    room = (np.pi - last[4]) * sc.K
    assert lead_of_a_line(comp, roll, 5)[4] == 20.0 and added(last, 5) < room
    moving = command_with_lead(comp, last, lead_of_a_line(comp, roll, 5), side)
    assert goal(arm) == units(arm, moving) and goal_writes(arm) == 6
    (timer,) = live(timers)
    state = arm.servo_compensation
    stream = state.streams["full"]
    before = state_of(stream)

    q = [angle + step for angle, step in zip(last, roll)]
    clock.advance(DT)
    assert q[4] < np.pi and added(q, 6) > (np.pi - q[4]) * sc.K
    r = write(client, q)
    assert r.status_code == 400 and "command" in r.json()["detail"]
    assert goal_writes(arm) == 6 and goal(arm) == units(arm, moving)
    assert live(timers) == [timer] and state_of(stream) == before
    assert raw(client) == (units(arm, last), "full")

    # The stream goes on from the last accepted request, as if the refused one never
    # came: a slower step, and the lead comes down from 20 by 4 (not from 24)
    slow = [0.0, 0.0, 0.0, 0.0, 0.005, 0.0]
    q = [angle + step for angle, step in zip(last, slow)]
    assert 0 < lags(comp)[4] * speed_ticks(comp, slow)[4] < 16.0
    clock.advance(DT)
    assert write(client, q).status_code == 200
    slow_side = np.tanh(speed_ticks(comp, slow) / sc.V0)
    assert goal(arm) == units(
        arm, command_with_lead(comp, q, [0.0, 0.0, 0.0, 0.0, 16.0], slow_side)
    )
    assert timer.cancelled
    (timer2,) = live(timers)
    timer2.fire()
    assert goal(arm) == rest_units(arm, q)


def test_a_refused_request_does_not_move_the_lead(client, arms, config_file, clock, timers):
    """
    The stream's lead is part of what a refused request must leave alone (runtime
    version 5 keeps it between requests). Refused here: a request that holds the
    line's joints and sends the elbow out of range. Had it been stepped, the base's
    lead would have gone from 20 to 16 and the elbow's from 0 to 4.
    """
    arm, comp = arms[1], compensator()
    last = line(client, clock, 5)
    stream = arm.servo_compensation.streams["full"]
    lead = stream._lead.copy()
    assert np.allclose(lead, lead_of_a_line(comp, DQ, 5), atol=1e-9) and lead[0] == -20.0

    bad = list(last)
    bad[2] = 4.0
    clock.advance(DT)
    assert write(client, bad).status_code == 400
    assert np.array_equal(stream._lead, lead)

    # The line goes on: the 6th moving request, with 24 ticks of lead on the base
    q = [angle + step for angle, step in zip(last, DQ)]
    clock.advance(DT)
    assert write(client, q).status_code == 200
    side = np.tanh(speed_ticks(comp, DQ) / sc.V0)
    lead6 = lead_of_a_line(comp, DQ, 6)
    assert lead6[0] == -24.0
    assert goal(arm) == units(arm, command_with_lead(comp, q, lead6, side))


def test_a_refused_static_request_leaves_the_timer_of_the_full_stream(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    last = start_stream(client, clock)
    state = arm.servo_compensation
    before = state_of(state.streams["full"])
    (timer,) = live(timers)
    bad = list(last)
    bad[0] = -3.5
    clock.advance(DT)
    assert write(client, bad, terms="static").status_code == 400
    assert live(timers) == [timer] and goal_writes(arm) == 2
    assert state_of(state.streams["full"]) == before and "static" not in state.streams
    assert raw(client) == (units(arm, last), "full")
    timer.fire()
    assert goal_writes(arm) == 3 and goal(arm) == rest_units(arm, last)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), 1e308])
def test_a_first_request_that_is_refused_leaves_no_stream(client, arms, config_file, bad):
    arm = arms[1]
    angles = list(Q)
    angles[3] = bad
    r = client.post(
        "/joints/write",
        params={**RIGHT, "compensate": "full"},
        content=(
            '{"angles": ['
            + ", ".join("NaN" if a != a else "Infinity" if a == float("inf") else "-Infinity" if a == -float("inf") else repr(a) for a in angles)
            + '], "unit": "rad"}'
        ),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400 and arm.motors_bus.calls == []
    state = arm.servo_compensation
    assert state is None or (state.streams == {} and state.terms is None)
    assert write(client, Q).status_code == 200
    assert goal(arm) == units(arm, compensator().command(Q, np.zeros(5), np.zeros(5)))
