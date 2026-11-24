"""
Guards that an independent review found untested: with the code removed, every
test still passed. Each test here fails when its guard is removed (the commit
message says how that was checked).

- the lock: a writer in another thread waits for a compensated write in progress
- RestTimer.cancel from another thread than the loop's
- the rest timer reads Torque_Enable from the bus, not from the 0.25 s cache
- the refusal of a robot that is not an SO-100/SO-101
- arms found again after a USB drop: new objects, and the old ones' timers are dead
"""

import asyncio
import threading
import time

import numpy as np
from s1a.conftest import LEFT_SERIAL, RIGHT_SERIAL, FakeRCM, RescanRCM, client_for

from .conftest import (
    DT,
    LEFT,
    REAL_REST_TIMER,
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


def test_a_writer_in_another_thread_waits_for_the_compensated_write_then_voids_it(
    client, arms, config_file, clock, timers
):
    """
    Truly concurrent: the compensated write is held open on the bus while another
    thread calls a hardware writer. That writer must not reach the bus before the
    compensated write is over (the lock), and must void the streams afterwards.
    """
    arm = arms[1]
    assert write(client, Q).status_code == 200
    bus, real_write = arm.motors_bus, arm.motors_bus.write
    order, other_on_bus, others, reached_while_open = [], threading.Event(), [], []

    def write_on_the_bus(data_name, values, motor_names=None):
        if threading.current_thread().name == "other-mover":
            other_on_bus.set()
            order.append("other mover")
        elif data_name == "Goal_Position" and not others:
            # The compensated write is on the bus. Another mover starts now
            other = threading.Thread(
                name="other-mover", target=arm.write_motor_position, args=(6, 2000)
            )
            others.append(other)
            other.start()
            reached_while_open.append(other_on_bus.wait(0.2))
            order.append("compensated write")
        return real_write(data_name, values, motor_names)

    bus.write = write_on_the_bus
    q = list(Q)
    q[1] -= 0.02
    clock.advance(DT)
    assert write(client, q).status_code == 200
    others[0].join(10)
    assert not others[0].is_alive()

    assert reached_while_open == [False]
    assert order == ["compensated write", "other mover"]
    # The other mover came second: the servos hold its goal and the streams are void
    assert goal(arm)[5] == 2000
    state = arm.servo_compensation
    assert state.terms is None and state.requested_position is None
    assert all(stream._q is None for stream in state.streams.values())
    assert len(timers) == 1 and live(timers) == []


def test_a_timer_cancelled_from_another_thread_is_cancelled_on_its_loop(
    client, arms, config_file, clock, real_timers
):
    """
    With torque on, so that only the cancellation can show: the callback of a
    cancelled timer would do nothing anyway (its generation is gone).
    """
    arm = arms[1]
    start_stream(client, clock)
    (timer,) = real_timers
    assert not timer._handle.cancelled()
    # From this thread, which is not the loop's: a hardware writer voids the streams
    assert arm.write_motor_position(6, 2000) is True
    deadline = time.monotonic() + 0.06  # the timer is due 0.1 s after it was made
    while not timer._handle.cancelled() and time.monotonic() < deadline:
        time.sleep(0.002)
    assert timer._handle.cancelled()
    assert arm.motors_bus.regs["Torque_Enable"] == [1] * 6 and goal_writes(arm) == 3


def test_a_timer_can_be_cancelled_after_its_loop_is_closed_and_from_another_loop():
    fired = []

    async def make():
        # The server's own class: this directory's tests get a stand-in by default
        return REAL_REST_TIMER(0.05, lambda: fired.append(1))

    loop = asyncio.new_event_loop()
    timer = loop.run_until_complete(make())
    loop.close()
    timer.cancel()  # as the move to sleep at exit, after the server's loop is closed

    async def from_another_loop():
        timer.cancel()

    asyncio.run(from_another_loop())

    # A loop that runs in another thread: cancelled from here before it is due
    loop2 = asyncio.new_event_loop()
    thread = threading.Thread(target=loop2.run_forever)
    thread.start()
    try:
        made = asyncio.run_coroutine_threadsafe(make(), loop2).result(5)
        made.cancel()
        time.sleep(0.12)
    finally:
        loop2.call_soon_threadsafe(loop2.stop)
        thread.join(5)
        loop2.close()
    assert fired == [] and made._handle.cancelled()


def test_the_rest_timer_reads_torque_from_the_bus_not_from_the_cache(
    client, arms, config_file, clock, timers
):
    arm = arms[1]
    start_stream(client, clock)
    # A read a moment ago says torque is on; then it goes off without the server
    assert arm.read_torque_enabled() == ([True] * 6, 0.0)
    arm.motors_bus.regs["Torque_Enable"] = [0] * 6
    assert arm.read_torque_enabled()[0] == [True] * 6  # the cache still says on
    calls = len(arm.motors_bus.calls)
    live(timers)[0].fire()
    assert arm.motors_bus.calls[calls:] == [("read", "Torque_Enable")]
    assert goal_writes(arm) == 2 and arm.servo_compensation.terms is None


class NotAnSO100:
    """A robot of another kind that can write joint positions, with a serial of the config."""

    name = "other-arm"
    SERIAL_ID = RIGHT_SERIAL
    SERVO_IDS = [1, 2, 3, 4, 5, 6]
    is_connected = True

    def __init__(self) -> None:
        self.writes: list = []

    def write_joint_positions(self, angles, unit, joints_ids=None):  # type: ignore
        self.writes.append((list(angles), unit))
        return True


def test_a_robot_that_is_not_an_so100_is_refused(config_file, hardware_mode):
    robot = NotAnSO100()
    with client_for(FakeRCM([robot])) as client:
        for terms in ("full", "static"):
            r = write(client, Q, terms=terms)
            assert r.status_code == 400, r.text
            assert r.json()["detail"] == "Robot does not support servo compensation"
        assert robot.writes == []
        r = client.post("/joints/write", params=RIGHT, json={"angles": Q, "unit": "rad"})
        assert r.status_code == 200 and robot.writes == [(Q, "rad")]


def test_arms_found_again_after_a_usb_drop_are_new_and_the_old_timers_are_dead(
    arm_factory, config_file, clock, timers
):
    old = [arm_factory(LEFT_SERIAL), arm_factory(RIGHT_SERIAL)]
    new = [arm_factory(RIGHT_SERIAL), arm_factory(LEFT_SERIAL)]  # the ids swapped
    rcm = RescanRCM(old, new)
    with client_for(rcm) as client:
        start_stream(client, clock)
        start_stream(client, clock, arm=LEFT)
        assert len(live(timers)) == 2
        # A request that makes the manager scan: it finds other ports and rebuilds
        assert client.post("/joints/read", params={"robot_id": 5}).status_code == 400
        assert rcm._all_robots == new
        assert live(timers) == []
        calls = [list(arm.motors_bus.calls) for arm in old]
        clock.advance(1.0)
        for arm in old:
            arm.is_connected = True  # even if an old object were thought connected
        for timer in timers:
            timer.fire()
        assert [list(arm.motors_bus.calls) for arm in old] == calls
        assert all(arm.servo_compensation.terms is None for arm in old)
        for arm in old:
            arm.is_connected = False
        # The new objects start empty
        assert all(arm.motors_bus.calls == [] for arm in new)
        assert all(arm.servo_compensation is None for arm in new)
        # And a request by serial reaches the new object with that serial's model
        assert write(client, Q).status_code == 200
        assert goal_writes(new[0]) == 1 and goal_writes(new[1]) == 0
        fresh = compensator(RIGHT_SERIAL).command(Q, np.zeros(5), np.zeros(5))
        assert goal(new[0]) == units(new[0], fresh)
        # A stale robot_id with the serial is refused, not obeyed
        r = write(client, Q, arm={"robot_id": 1, "serial": RIGHT_SERIAL})
        assert r.status_code == 409 and goal_writes(new[1]) == 0
