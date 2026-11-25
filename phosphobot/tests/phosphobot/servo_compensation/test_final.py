"""
The last request of a move, named by its caller: POST /joints/write?compensate=...
&final=true. Its command carries no speed term, so the servo is not led past the
request and nothing has to be taken back: no rest timer. The friction side is the
one the joint arrives from.
"""

import time

import numpy as np
import pytest

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
    lead_of_a_line,
    line,
    speed_ticks,
    start_stream,
    units,
    write,
)
from .test_default_path import BASE_RESPONSE, BASE_UNITS_RAD


def moved_request():
    q = list(Q)
    q[0] += 0.02
    q[1] -= 0.02
    return q


def test_a_final_write_is_the_request_at_speed_0_from_the_side_of_the_step(
    client, arms, config_file, clock, timers
):
    """A move of one step: no command lay past its last request, every joint keeps its side."""
    arm, comp = arms[1], compensator()
    q2 = moved_request()
    assert write(client, Q).status_code == 200
    clock.advance(DT)
    r = write(client, q2, final=True)
    assert r.status_code == 200

    # The step's speed gives the side; the command has no lag term
    v = np.zeros(5)
    v[0] = comp.signs[0] * sc.K * 0.02 / DT
    v[1] = comp.signs[1] * sc.K * -0.02 / DT
    side = np.tanh(v / sc.V0)
    want = np.clip(
        -comp.error_ticks(q2, np.zeros(5), side, sc.TERMS), -comp.max_ticks, comp.max_ticks
    )
    moved = np.array(goal(arm)) - np.array(units(arm, q2))
    assert np.all(np.abs(moved[:5] - want) <= 1.0), (moved, want)
    assert moved[5] == 0 and goal_writes(arm) == 2
    # Exactly the stream's own final step: neither the moving command nor the neutral one
    final_command = comp.command(q2, np.zeros(5), side, sc.TERMS)
    assert goal(arm) == units(arm, final_command)
    assert final_command != comp.command(q2, v, side, sc.TERMS)
    assert final_command != comp.command(q2, np.zeros(5), np.zeros(5), sc.TERMS)

    # Nothing to take back: no rest timer
    state = arm.servo_compensation
    assert state.streams["full"].pending is False and timers == []
    assert r.json()["compensation"] == {
        "terms": "full",
        "correction_ticks": moved[:5].tolist(),
        "final": True,
        "stop_files": 0,
    }
    b = client.post("/joints/read/raw", params=RIGHT).json()
    assert (b["requested_position"], b["compensation"]) == (units(arm, q2), "full")


def test_a_joint_that_was_commanded_past_the_final_request_gets_no_friction_side(
    client, arms, config_file, clock, timers
):
    """
    Runtime version 5. After five requests of a line the base's command leads its
    request by 20 ticks and the shoulder lift's by 12 (all of its lag x speed); the
    step to the final request is 13 ticks on both. The base's previous command
    already lay past the final request: it runs on and comes to rest from either
    side, so it gets no friction side. The shoulder lift arrives from the side it
    moved on and keeps it.
    """
    arm, comp = arms[1], compensator()
    q = line(client, clock, 5)
    v = speed_ticks(comp, DQ)
    side, lead = np.tanh(v / sc.V0), lead_of_a_line(comp, DQ, 5)
    step = speed_ticks(comp, DQ) * DT
    assert lead[0] == -20.0 and -12.5 < lead[1] < -11.5 and -13.5 < step[0] == step[1] < -12.5
    assert goal(arm) == units(arm, command_with_lead(comp, q, lead, side))

    final = [angle + dq for angle, dq in zip(q, DQ)]
    clock.advance(DT)
    r = write(client, final, final=True)
    assert r.status_code == 200
    side_left = side * np.array([0.0, 1.0, 1.0, 1.0, 1.0])
    want = comp.command(final, np.zeros(5), side_left, sc.TERMS)
    assert goal(arm) == units(arm, want)
    # On the base that is the neutral command; with its side it would be a tick off
    neutral = comp.command(final, np.zeros(5), np.zeros(5), sc.TERMS)
    assert want[0] == neutral[0] != comp.command(final, np.zeros(5), side, sc.TERMS)[0]
    assert want[1] != neutral[1]
    stream = arm.servo_compensation.streams["full"]
    assert stream.pending is False and not np.any(stream._lead)
    assert all(timer.cancelled for timer in timers)

    # The base stays without a side while it rests
    clock.advance(DT)
    assert write(client, final).status_code == 200
    assert goal(arm) == units(arm, want) and stream.pending is False
    assert all(timer.cancelled for timer in timers)


def test_a_final_request_that_repeats_the_last_one_takes_the_side_of_every_leading_joint(
    client, arms, config_file, clock, timers
):
    """The move has already stopped: every command that led lay past this request."""
    arm, comp = arms[1], compensator()
    q = line(client, clock, 5)
    clock.advance(DT)
    assert write(client, q, final=True).status_code == 200
    assert goal(arm) == units(arm, comp.command(q, np.zeros(5), np.zeros(5), sc.TERMS))
    assert arm.servo_compensation.streams["full"].pending is False


def test_a_final_write_cancels_the_timer_of_the_write_before(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    q = start_stream(client, clock)
    (timer,) = timers
    assert not timer.cancelled
    q[1] -= 0.02
    clock.advance(DT)
    assert write(client, q, final=True).status_code == 200
    assert timer.cancelled and timers == [timer]
    # Also when the loop had already taken the callback: nothing reaches the bus
    calls = list(arm.motors_bus.calls)
    clock.advance(0.3)
    timer.fire()
    assert arm.motors_bus.calls == calls and goal_writes(arm) == 3


def test_after_a_final_write_no_rest_command_comes(
    client, arms, config_file, clock, real_timers
):
    """With the server's own timers on the event loop. 0.2 s of real time."""
    arm = arms[1]
    q = start_stream(client, clock)
    q[1] -= 0.02
    clock.advance(DT)
    assert write(client, q, final=True).status_code == 200
    final_goal = goal(arm)
    time.sleep(0.2)  # REST_DELAY_S of the write before was 0.1 s
    assert goal_writes(arm) == 3 and goal(arm) == final_goal


def test_after_a_final_write_the_stream_goes_on(client, arms, config_file, clock, timers):
    arm, mirror = arms[1], sc.Stream(compensator())
    q2 = moved_request()
    write(client, Q)
    mirror.step(Q, clock.t)
    clock.advance(DT)
    write(client, q2, final=True)
    mirror.step(q2, clock.t, final=True)
    q3 = list(q2)
    q3[1] -= 0.02
    clock.advance(DT)
    assert write(client, q3).status_code == 200
    command = mirror.step(q3, clock.t)
    assert goal(arm) == units(arm, command)
    # It moves again: a speed term, and its timer
    assert command != compensator().command(q3, np.zeros(5), mirror._dir, sc.TERMS)
    assert arm.servo_compensation.streams["full"].pending and len(timers) == 1


def test_final_without_compensate_is_refused(client, arms, config_file):
    """A caller that believes it is compensated is not served an uncompensated write."""
    body = {"angles": Q, "unit": "rad"}
    for value in ("true", "1"):
        r = client.post("/joints/write", params={**RIGHT, "final": value}, json=body)
        assert r.status_code == 400, r.text
        assert "final" in r.json()["detail"] and "compensate" in r.json()["detail"]
    assert arms[1].motors_bus.calls == [] and arms[1].servo_compensation is None
    # final=false is the default: the base write
    r = client.post("/joints/write", params={"robot_id": 1, "final": "false"}, json=body)
    assert (r.status_code, r.content) == (200, BASE_RESPONSE)
    assert goal(arms[1]) == BASE_UNITS_RAD
    r = client.post("/joints/write", params={**RIGHT, "final": "perhaps"}, json=body)
    assert r.status_code == 422 and goal_writes(arms[1]) == 1


@pytest.mark.parametrize("final", [True, False])
def test_with_static_final_changes_nothing_in_the_command(
    client, arms, config_file, clock, timers, final
):
    arm, comp = arms[1], compensator()
    q2 = moved_request()
    write(client, Q, terms="static")
    clock.advance(DT)
    r = write(client, q2, terms="static", final=final)
    assert r.status_code == 200 and r.json()["compensation"]["final"] is final
    assert goal(arm) == units(arm, comp.command(q2, np.zeros(5), np.zeros(5), sc.STATIC))
    assert timers == [] and not arm.servo_compensation.streams["static"].pending


def test_a_final_write_that_cannot_be_compensated_is_refused_as_any(client, arms):
    r = write(client, Q, final=True)
    assert r.status_code == 409 and arms[1].motors_bus.calls == []
