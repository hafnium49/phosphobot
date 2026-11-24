"""
A compensated request that is refused before anything reaches the bus changes
nothing: the stream is as it was after the last accepted request, and the rest
command of that request still comes. (A refused request used to cancel the pending
rest command and never replace it: the servo kept the command with the speed lead.)
"""

import numpy as np
import pytest

from phosphobot.hardware import servo_compensation as sc

from .conftest import (
    DT,
    RIGHT,
    Q,
    compensator,
    goal,
    goal_writes,
    start_stream,
    units,
    write,
)

STREAM_STATE = ("_q", "_t", "_dir", "_intervals", "pending")


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
    """The wrist roll near +pi: the request is inside -pi..pi, its command is not."""
    arm, mirror = arms[1], sc.Stream(compensator())
    q = list(Q)
    q[4] = 3.00
    assert write(client, q).status_code == 200
    mirror.step(q, clock.t)
    q[4] = 3.02
    clock.advance(DT)
    assert write(client, q).status_code == 200
    moving = mirror.step(q, clock.t)
    last = list(q)
    (timer,) = live(timers)
    state = arm.servo_compensation
    before = state_of(state.streams["full"])

    q[4] = 3.10
    clock.advance(DT)
    assert q[4] < np.pi
    r = write(client, q)
    assert r.status_code == 400 and "command" in r.json()["detail"]
    assert goal_writes(arm) == 2 and goal(arm) == units(arm, moving)
    assert live(timers) == [timer] and state_of(state.streams["full"]) == before
    assert raw(client) == (units(arm, last), "full")

    # The stream goes on from the last accepted request, as if the refused one never came
    q[4] = 3.03
    clock.advance(DT)
    assert write(client, q).status_code == 200
    assert goal(arm) == units(arm, mirror.step(q, clock.t)) and timer.cancelled
    (timer2,) = live(timers)
    timer2.fire()
    assert goal(arm) == rest_units(arm, q)


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
