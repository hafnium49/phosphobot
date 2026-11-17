"""
The loops that soften and restore the PID gains of several servos (gravity
compensation, leader-follower) go on when one servo fails: the failed servo is
logged and skipped, the clean-up reaches the end, and the running signal is cleared.
Only enable_torque fails on a gain that was not written (see test_writes.py).
"""

import asyncio

import pytest

from phosphobot.control_signal import ControlSignal
from phosphobot.leader_follower import LeaderFollowerThread, RobotPair

from .conftest import FakeBus

# FakeBus reports 12 V. Gains of the gravity loop at 12 V, and what it restores
GRAVITY_P = [1, 3, 3, 1, 1, 1]
DEFAULT_P = [6, 6, 6, 10, 10, 10]


class FlakyBus(FakeBus):
    """Fails exactly one Torque_Enable read: the n-th after fail_read_number is set."""

    fail_read_number = None

    def read(self, data_name, motor_names=None):
        if data_name == "Torque_Enable" and self.fail_read_number is not None:
            self.fail_read_number -= 1
            if self.fail_read_number == 0:
                self.fail_read_number = None
                self.calls.append(("read", data_name))
                raise ConnectionError("one transient read failure")
        return super().read(data_name, motor_names)


# enable_torque reads Torque_Enable once per servo, then reads it back
READS_OF_ENABLE_TORQUE = 7


@pytest.mark.asyncio
async def test_gravity_start_skips_a_servo_whose_gains_could_not_be_set(arms):
    arm, bus = arms[1], FlakyBus()
    arm.motors_bus = bus
    calibration_p = int(arm.config.pid_gains[1].p_gain)
    bus.fail_read_number = READS_OF_ENABLE_TORQUE + 2  # the second servo of the set-up
    signal = ControlSignal()
    signal.start()
    task = asyncio.ensure_future(arm.gravity_compensation_loop(signal))
    await asyncio.sleep(0.8)  # set-up done (6 x 0.05 s), loop running
    assert not task.done() and signal.is_in_loop()
    assert bus.regs["P_Coefficient"] == [1, calibration_p, 3, 1, 1, 1]
    signal.stop()
    await asyncio.wait_for(task, 3)
    assert bus.regs["P_Coefficient"] == DEFAULT_P


@pytest.mark.asyncio
async def test_gravity_cleanup_restores_the_other_servos_when_one_fails(arms):
    arm, bus = arms[1], FlakyBus()
    arm.motors_bus = bus
    signal = ControlSignal()
    signal.start()
    task = asyncio.ensure_future(arm.gravity_compensation_loop(signal))
    await asyncio.sleep(0.8)
    assert bus.regs["P_Coefficient"] == GRAVITY_P
    bus.fail_read_number = 2  # the second servo of the clean-up
    signal.stop()
    await asyncio.wait_for(task, 3)
    assert bus.regs["P_Coefficient"] == [6, 3, 6, 10, 10, 10]


@pytest.mark.asyncio
async def test_gravity_loop_that_ends_by_itself_clears_its_signal(arms):
    signal = ControlSignal()
    # No voltage: the loop returns before it starts
    arms[1].is_connected = False
    signal.start()
    await asyncio.wait_for(arms[1].gravity_compensation_loop(signal), 3)
    assert not signal.is_in_loop()
    # The loop dies of an error
    arms[0].read_joints_position = lambda **kwargs: 1 / 0
    signal.start()
    with pytest.raises(ZeroDivisionError):
        await asyncio.wait_for(arms[0].gravity_compensation_loop(signal), 3)
    assert not signal.is_in_loop()


def leader_follower_thread(arms, signal):
    leader, follower = arms
    thread = LeaderFollowerThread(
        robot_pairs=[RobotPair(leader=leader, follower=follower)],
        control_signal=signal,
        invert_controls=False,
        enable_gravity_compensation=True,
        compensation_values=None,
        sim=leader.sim,
    )
    return thread, leader, follower


def test_leader_follower_setup_skips_a_servo_whose_gains_could_not_be_set(arms):
    signal = ControlSignal()
    signal.start()
    thread, leader, follower = leader_follower_thread(arms, signal)
    for arm in arms:  # already initialised: the set-up does not move them
        arm.initial_position, arm.initial_orientation_rad = [0, 0, 0], [0, 0, 0]
    bus = FlakyBus()
    leader.motors_bus = bus
    calibration_p = int(leader.config.pid_gains[1].p_gain)
    # The real one returns None with numpy 2.4 (int() of a one-element array),
    # and the set-up then stops before it sets any gain
    leader._get_pid_gains_motor = lambda servo_id: (16, 0, 32)
    bus.fail_read_number = READS_OF_ENABLE_TORQUE + 2
    thread._setup_robots()
    assert signal.is_in_loop()
    assert bus.regs["P_Coefficient"] == [1, calibration_p, 3, 1, 1, 1]


@pytest.mark.parametrize("failure", ["one torque read", "every gain write", "no gains"])
def test_leader_follower_cleanup_always_releases_both_arms(arms, failure):
    signal = ControlSignal()
    thread, leader, follower = leader_follower_thread(arms, signal)
    bus = FlakyBus()
    leader.motors_bus = bus
    thread.original_pid_gains[leader.name] = [(16, 0, 32)] * 6
    if failure == "one torque read":
        bus.fail_read_number = READS_OF_ENABLE_TORQUE + 2
    elif failure == "every gain write":
        bus.fail.add("write:P_Coefficient")
    else:
        thread.original_pid_gains[leader.name] = [(16, 0, 32), None] + [(16, 0, 32)] * 4
    thread._cleanup_robots()
    assert bus.regs["Torque_Enable"] == [0] * 6
    assert follower.motors_bus.regs["Torque_Enable"] == [0] * 6
    if failure == "one torque read":
        # The servo that failed keeps the gain that enable_torque wrote
        calibration_p = int(leader.config.pid_gains[1].p_gain)
        assert bus.regs["P_Coefficient"] == [16, calibration_p, 16, 16, 16, 16]


def test_leader_follower_run_cleans_up_and_clears_its_signal_when_setup_fails(arms):
    signal = ControlSignal()
    signal.start()
    thread, leader, follower = leader_follower_thread(arms, signal)

    def setup_that_fails():
        raise RuntimeError("set-up failed")

    thread._setup_robots = setup_that_fails
    thread.run()  # in this thread: nothing is started
    assert not signal.is_in_loop()
    assert leader.motors_bus.regs["Torque_Enable"] == [0] * 6
    assert follower.motors_bus.regs["Torque_Enable"] == [0] * 6
