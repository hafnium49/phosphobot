"""
The rest command. The last command of a moving "full" stream carries lag x speed;
a servo left with it rests past the request. When no further compensated request
comes for the arm within REST_DELAY_S, the server writes the stream's rest command
once. Nothing is written when the stream continues, or when anything else wrote
the arm's goal in between.
"""

import time

import numpy as np
import pytest

from phosphobot import compensated_write
from phosphobot.hardware import servo_compensation as sc

from .conftest import (
    DT,
    OTHER_WRITERS,
    RIGHT,
    Q,
    compensator,
    goal,
    goal_writes,
    start_stream,
    units,
    write,
)


def live(timers):
    return [timer for timer in timers if not timer.cancelled]


def mirror_of_start_stream(clock):
    """The stream of the right arm after start_stream, computed by the runtime alone."""
    mirror = sc.Stream(compensator())
    q = list(Q)
    q[0] += 0.02
    q[1] -= 0.02
    mirror.step(Q, clock.t - DT)
    return mirror, q, mirror.step(q, clock.t)


def test_a_stream_that_stops_gets_its_rest_command_once(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    last = start_stream(client, clock)
    mirror, q, moving = mirror_of_start_stream(clock)
    assert goal(arm) == units(arm, moving) and goal_writes(arm) == 2
    (timer,) = live(timers)
    assert timer.delay_s == pytest.approx(1.5 * DT)

    clock.advance(timer.delay_s)
    timer.fire()
    rest = mirror.rest(clock.t)
    assert goal_writes(arm) == 3 and goal(arm) == units(arm, rest)
    # The request at speed 0: not the moving command, and the gripper as requested
    assert goal(arm) != units(arm, moving) and goal(arm)[5] == units(arm, last)[5]
    state = arm.servo_compensation
    assert state.terms == "full" and state.requested_position == units(arm, last)
    assert not state.streams["full"].pending and live(timers) == [timer]

    # Once: whatever fires again reaches the bus no more
    calls = list(arm.motors_bus.calls)
    for made in timers:
        made.fire()
    assert arm.motors_bus.calls == calls and arms[0].motors_bus.calls == []

    # And the stream goes on from rest
    q[1] -= 0.02
    clock.advance(DT)
    assert write(client, q).status_code == 200
    assert goal(arm) == units(arm, mirror.step(q, clock.t))


def test_a_stream_that_continues_gets_no_rest_command(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    q = start_stream(client, clock)
    for _ in range(5):
        q[1] -= 0.02
        clock.advance(DT)
        assert write(client, q).status_code == 200
        # One timer at most: each request cancels the timer of the one before
        assert len(live(timers)) == 1
        for timer in timers[:-1]:
            timer.fire()
    assert goal_writes(arm) == 7 and len(timers) == 6


def test_there_is_no_timer_without_a_speed_term(client, arms, config_file, clock, timers):
    arm = arms[1]
    # The first request of a stream has no speed
    assert write(client, Q).status_code == 200
    assert timers == []
    # "static" never has a speed term
    last = start_stream(client, clock, terms="static")
    assert timers == [] and not arm.servo_compensation.streams["static"].pending
    # A stream that is asked the same pose again is at rest: its timer is cancelled
    last = start_stream(client, clock)
    assert len(live(timers)) == 1
    clock.advance(DT)
    assert write(client, last).status_code == 200
    assert live(timers) == [] and goal_writes(arm) == 6


@pytest.mark.parametrize(
    "interval_s,delay_s",
    [(0.005, 0.08), (0.02, 0.08), (1 / 15, 0.1), (0.19, 0.285), (0.5, 0.30), (30.0, 0.30)],
)
def test_the_delay_is_one_and_a_half_usual_intervals_within_bounds(
    client, arms, config_file, clock, timers, interval_s, delay_s
):
    q = list(Q)
    for _ in range(4):
        assert write(client, q).status_code == 200
        q[1] -= 0.02
        clock.advance(interval_s)
    stream = arms[1].servo_compensation.streams["full"]
    # The stream's own usual interval: the one its speed is taken over
    usual = compensated_write.usual_interval_s(stream)
    assert usual == pytest.approx(min(max(interval_s, sc.MIN_DT_S), sc.MAX_DT_S))
    assert compensated_write.rest_delay_s(stream) == pytest.approx(delay_s)
    assert live(timers)[0].delay_s == pytest.approx(delay_s)


@pytest.mark.parametrize("name", list(OTHER_WRITERS))
def test_another_writer_of_the_goal_cancels_the_rest_command(
    client, arms, config_file, clock, timers, no_waits, name
):
    arm = arms[1]
    arm.initial_position, arm.initial_orientation_rad = np.zeros(3), np.zeros(3)
    start_stream(client, clock)
    (timer,) = live(timers)

    OTHER_WRITERS[name](client, arm)

    assert timer.cancelled and live(timers) == []
    # Also when the loop had already taken the callback: nothing reaches the bus
    arm.is_connected = True
    calls = list(arm.motors_bus.calls)
    clock.advance(timer.delay_s)
    timer.fire()
    assert arm.motors_bus.calls == calls


def test_no_rest_command_for_an_arm_whose_torque_is_off(
    client, arms, config_file, clock, timers
):
    """Torque that went off without the server (the servo's protection, a power cut)."""
    arm = arms[1]
    start_stream(client, clock)
    arm.motors_bus.regs["Torque_Enable"] = [1, 1, 0, 1, 1, 1]
    clock.advance(0.3)
    live(timers)[0].fire()
    assert goal_writes(arm) == 2
    assert arm.servo_compensation.terms is None


@pytest.mark.parametrize(
    "failure",
    [
        lambda arm: arm.motors_bus.fail.add("write:Goal_Position"),
        lambda arm: arm.motors_bus.fail.add("read:Torque_Enable"),
        lambda arm: setattr(arm, "is_connected", False),
    ],
)
def test_a_rest_command_that_cannot_be_written_is_logged_and_voids_the_stream(
    client, arms, config_file, clock, timers, failure
):
    from loguru import logger

    arm = arms[1]
    start_stream(client, clock)
    failure(arm)
    logged = []
    sink = logger.add(logged.append, level="WARNING")
    try:
        # Nothing is raised into the event loop
        live(timers)[0].fire()
    finally:
        logger.remove(sink)
    assert arm.motors_bus.regs["Goal_Position"] == units(
        arm, mirror_of_start_stream(clock)[2]
    )
    assert any("rest command" in message and "5A68009540" in message for message in logged)
    state = arm.servo_compensation
    assert state.terms is None and state.requested_position is None


def test_on_the_event_loop_the_rest_command_comes_by_itself(
    client, arms, config_file, clock, real_timers
):
    """The server's own timer, on the loop the endpoints run on. 0.4 s of real time."""
    arm = arms[1]
    start_stream(client, clock)
    mirror, _, _ = mirror_of_start_stream(clock)
    assert goal_writes(arm) == 2
    time.sleep(0.25)  # REST_DELAY_S is 0.1 s here
    assert goal_writes(arm) == 3 and goal(arm) == units(arm, mirror.rest(clock.t))
    assert client.post("/joints/read/raw", params=RIGHT).status_code == 200

    # A timer that is cancelled from another thread than the loop's does not fire
    start_stream(client, clock)
    assert goal_writes(arm) == 5
    assert arm.disable_torque() is True
    time.sleep(0.15)
    assert goal_writes(arm) == 5
