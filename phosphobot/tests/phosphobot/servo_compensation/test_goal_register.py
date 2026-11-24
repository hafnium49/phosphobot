"""
The rest timer writes only over its own stream's command. Before it writes, it reads
the six Goal_Position registers from the bus: if they are not the motor units of the
last command the stream wrote, somebody else wrote this arm (a mover in a thread that
slipped between, another process on the bus) and nothing is written.
"""

import threading

import numpy as np
import pytest
from loguru import logger

from .conftest import (
    RIGHT,
    compensator,
    goal,
    goal_writes,
    start_stream,
    units,
    write,
)
from .test_refused_request import raw, rest_units

GOAL_READ = ("read_with_motor_ids", "Goal_Position")
NOT_THE_STREAMS = "the goal register is not the stream's last command: somebody else wrote this arm"


def live(timers):
    return [timer for timer in timers if not timer.cancelled]


def fire_and_listen(timer):
    logged = []
    sink = logger.add(logged.append, level="WARNING")
    try:
        timer.fire()
    finally:
        logger.remove(sink)
    return "".join(str(message) for message in logged)


def test_the_register_is_the_streams_command_and_the_rest_command_is_written_once(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    last = start_stream(client, clock)
    assert arm.servo_compensation._written_units == goal(arm)
    calls = len(arm.motors_bus.calls)
    logged = fire_and_listen(live(timers)[0])
    # Read from the bus at that moment, by servo id, then written
    assert arm.motors_bus.calls[calls:].count(GOAL_READ) == 1
    assert arm.motors_bus.calls[-1] == ("write", "Goal_Position")
    assert goal_writes(arm) == 3 and goal(arm) == rest_units(arm, last) and logged == ""
    # The rest command is the stream's last command now
    assert arm.servo_compensation._written_units == goal(arm)
    assert raw(client) == (units(arm, last), "full")


@pytest.mark.parametrize("servo", [0, 3, 5])
def test_a_register_that_differs_on_one_servo_is_somebody_elses(
    client, arms, config_file, clock, timers, servo
):
    arm = arms[1]
    start_stream(client, clock)
    arm.motors_bus.regs["Goal_Position"][servo] += 1
    others = goal(arm)
    logged = fire_and_listen(live(timers)[0])
    assert goal_writes(arm) == 2 and goal(arm) == others
    assert NOT_THE_STREAMS in logged and "5A68009540" in logged
    state = arm.servo_compensation
    assert state.terms is None and state._written_units is None
    assert all(stream._q is None for stream in state.streams.values())
    assert raw(client) == (None, None)


def test_a_goal_read_that_fails_twice_writes_nothing(client, arms, config_file, clock, timers):
    arm = arms[1]
    start_stream(client, clock)
    moving = goal(arm)
    arm.motors_bus.fail.add("read:Goal_Position")
    calls = len(arm.motors_bus.calls)
    logged = fire_and_listen(live(timers)[0])
    assert arm.motors_bus.calls[calls:].count(GOAL_READ) == 2
    assert goal_writes(arm) == 2 and goal(arm) == moving
    assert "rest command" in logged and arm.servo_compensation.terms is None


def test_a_goal_read_that_fails_once_does_not_cost_the_rest_command(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    last = start_stream(client, clock)
    bus, real, failed = arm.motors_bus, arm.motors_bus.read_with_motor_ids, []

    def failing_once(motor_models, motor_ids, data_name, **kwargs):
        if data_name == "Goal_Position" and not failed:
            failed.append(data_name)
            raise ConnectionError("Read failed due to communication error")
        return real(motor_models, motor_ids, data_name, **kwargs)

    bus.read_with_motor_ids = failing_once
    live(timers)[0].fire()
    assert failed and goal_writes(arm) == 3 and goal(arm) == rest_units(arm, last)


def test_a_mover_in_a_thread_that_slipped_between_is_not_written_over(
    client, arms, config_file, clock, timers
):
    """
    The choke point is check-then-act: a mover in another thread has passed it (the
    streams were void then) and has not reached the bus yet; compensated requests
    come and are written; then the other mover's write lands. The servos hold its
    goal, and the rest timer must not write over it.
    """
    arm = arms[1]
    assert write(client, [0.0] * 6).status_code == 200
    bus, in_write, go = arm.motors_bus, threading.Event(), threading.Event()
    real_write = bus.write

    def write_of_the_other_mover_waits(data_name, values, motor_names=None):
        if threading.current_thread().name == "other-mover":
            in_write.set()
            assert go.wait(10)
        return real_write(data_name, values, motor_names)

    bus.write = write_of_the_other_mover_waits
    other = threading.Thread(
        name="other-mover",
        target=arm.write_group_motor_position,
        args=(np.array([2048] * 6),),
    )
    other.start()
    assert in_write.wait(10)
    start_stream(client, clock)
    go.set()
    other.join()
    assert goal(arm) == [2048] * 6

    (timer,) = live(timers)
    clock.advance(timer.delay_s)
    logged = fire_and_listen(timer)
    assert goal(arm) == [2048] * 6 and goal_writes(arm) == 4
    assert NOT_THE_STREAMS in logged
    assert raw(client) == (None, None)
    # The next compensated request starts a stream
    assert write(client, [0.0] * 6).status_code == 200
    assert goal(arm) == units(arm, compensator().command([0.0] * 6, np.zeros(5), np.zeros(5)))
