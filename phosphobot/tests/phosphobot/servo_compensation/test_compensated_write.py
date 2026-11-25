"""
POST /joints/write?compensate=full|static: the command written is the request minus
the error the model predicts, the gripper is written as requested, and the response
says what was added.
"""

import numpy as np

from phosphobot.hardware import servo_compensation as sc

from .conftest import (
    DT,
    LEFT,
    LEFT_SERIAL,
    RIGHT_SERIAL,
    Q,
    command_with_lead,
    compensator,
    goal,
    goal_writes,
    lags,
    speed_ticks,
    units,
    write,
)


def predicted_ticks(q, v, direction, terms, serial=RIGHT_SERIAL):
    """The model's correction of the five arm joints, in ticks: what is to be added."""
    comp = compensator(serial)
    return np.clip(-comp.error_ticks(q, v, direction, terms), -comp.max_ticks, comp.max_ticks)


def step_down(q, joint=1, by=0.02):
    q = list(q)
    q[joint] -= by
    return q


def test_each_arm_joint_is_written_at_the_request_plus_the_predicted_correction(
    client, arms, config_file, clock
):
    arm = arms[1]
    r = write(client, Q)
    assert r.status_code == 200
    # The first request of a stream has no speed: the constant and the sag only
    want = predicted_ticks(Q, np.zeros(5), np.zeros(5), sc.TERMS)
    assert np.abs(want).max() > 3.0
    moved = np.array(goal(arm)) - np.array(units(arm, Q))
    # int() truncates the request and the command: one unit at most between them
    assert np.all(np.abs(moved[:5] - want) <= 1.0), (moved, want)
    assert moved[5] == 0
    assert goal_writes(arm) == 1 and arms[0].motors_bus.calls == []

    # The shoulder lift rises 0.02 rad every 1/15 s. The friction term joins at once.
    # The lead, lag x speed (12 ticks at this speed), comes in by 4 ticks a request
    # (runtime version 5): 4, 8, then all of it
    comp = compensator()
    dq = [0.0, -0.02, 0.0, 0.0, 0.0]
    v = speed_ticks(comp, dq)
    side = np.tanh(v / sc.V0)
    full = lags(comp)[1] * v[1]
    assert sc.LEAD_SLEW_TICKS == 4.0 and -12.5 < full < -11.5
    q = list(Q)
    for n, lead_1 in ((1, -4.0), (2, -8.0), (3, full), (4, full)):
        q = step_down(q)
        clock.advance(DT)
        assert write(client, q).status_code == 200
        lead = np.array([0.0, lead_1, 0.0, 0.0, 0.0])
        want = predicted_ticks(q, lead / lags(comp), side, sc.TERMS)
        at_rest = predicted_ticks(q, np.zeros(5), np.zeros(5), sc.TERMS)
        # What the speed adds on the shoulder lift: the lead, and a friction band of
        # under a tick at this pose
        assert 0.0 < abs((want - at_rest)[1] - lead_1) < 1.0
        moved = np.array(goal(arm)) - np.array(units(arm, q))
        assert np.all(np.abs(moved[:5] - want) <= 1.0), (n, moved, want)
        assert goal(arm) == units(arm, command_with_lead(comp, q, lead, side)), n
        assert moved[5] == 0 and goal_writes(arm) == 1 + n


def test_the_command_is_the_streams_own(client, arms, config_file, clock):
    """Exactly: the units written are those of stream.step(request, now)."""
    arm, mirror = arms[1], sc.Stream(compensator())
    q = list(Q)
    for _ in range(6):
        assert write(client, q).status_code == 200
        assert goal(arm) == units(arm, mirror.step(q, clock.t))
        q = step_down(q)
        clock.advance(DT)


def test_the_response_says_what_was_added(client, arms, config_file, clock):
    arm = arms[1]
    b = write(client, Q).json()
    moved = (np.array(goal(arm)) - np.array(units(arm, Q))).tolist()
    assert b["compensation"] == {
        "terms": "full",
        "correction_ticks": moved[:5],
        "final": False,
        "stop_files": 0,
    }
    assert (b["status"], b["robot_id"], b["serial"], b["bus_write"]) == (
        "ok",
        1,
        RIGHT_SERIAL,
        True,
    )
    assert write(client, Q, terms="static").json()["compensation"]["terms"] == "static"


def test_static_ignores_the_speed(client, arms, config_file, clock):
    arm, comp = arms[1], compensator()
    q2 = step_down(Q)
    write(client, Q, terms="static")
    clock.advance(DT)
    assert write(client, q2, terms="static").status_code == 200
    at_rest = comp.command(q2, np.zeros(5), np.zeros(5), sc.STATIC)
    assert goal(arm) == units(arm, at_rest)
    # The same two requests with every term do carry the speed
    arm.servo_compensation = None
    write(client, Q)
    clock.advance(DT)
    write(client, q2)
    assert goal(arm) != units(arm, at_rest)


def test_the_streams_of_two_arms_do_not_mix(client, arms, config_file, clock):
    left, right = arms
    mirror_left = sc.Stream(compensator(LEFT_SERIAL))
    mirror_right = sc.Stream(compensator(RIGHT_SERIAL))
    q = list(Q)
    for k in range(5):
        # The right arm moves; the left arm is asked the same pose again and again
        assert write(client, q).status_code == 200
        assert goal(right) == units(right, mirror_right.step(q, clock.t))
        clock.advance(DT / 2)
        assert write(client, Q, arm=LEFT).status_code == 200
        assert goal(left) == units(left, mirror_left.step(Q, clock.t))
        q = step_down(q)
        clock.advance(DT / 2)
    assert (goal_writes(left), goal_writes(right)) == (5, 5)
    # The two arms have their own parameters
    assert not np.allclose(
        compensator(LEFT_SERIAL).command(Q, np.zeros(5), np.zeros(5)),
        compensator(RIGHT_SERIAL).command(Q, np.zeros(5), np.zeros(5)),
    )


def test_the_streams_of_the_two_term_sets_do_not_mix(client, arms, config_file, clock):
    """A write with the other terms is a write by somebody else for a stream."""
    arm, comp = arms[1], compensator()
    write(client, Q)
    clock.advance(DT)
    write(client, step_down(Q))
    clock.advance(DT)
    write(client, Q, terms="static")
    clock.advance(DT)
    # The "full" stream starts again: no speed, no direction
    write(client, Q)
    assert goal(arm) == units(arm, comp.command(Q, np.zeros(5), np.zeros(5)))
