"""
The model assumes the PID gains of the arm's calibration. The gravity loop and the
leader-follower loop write other gains, and restore gains of their own choosing.
SO100Hardware.gains_are_calibration is True only while the gains last written by
this server are the calibration's (enable_torque writes them); a compensated write
while it is False is refused.

A server that has written no gains yet says True: the servos then hold what their
EEPROM and the last session left, which the server cannot know without reading.
"""

import asyncio

import pytest

from phosphobot.control_signal import ControlSignal
from phosphobot.hardware import so100

from .conftest import (
    RIGHT,
    Q,
    _Asyncio,
    goal,
    goal_writes,
    start_stream,
    units,
    write,
)

CHANGED = (
    "the servo gains were changed by this server (gravity or leader-follower loop); "
    "switch torque on again to write the calibration's gains"
)
TORQUE_ON = {"torque_status": True}


def refused_for_its_gains(client, arm):
    writes = goal_writes(arm)
    for terms in ("full", "static"):
        r = write(client, Q, terms=terms)
        assert r.status_code == 409 and CHANGED in r.json()["detail"], r.text
    assert goal_writes(arm) == writes


def test_a_server_that_wrote_no_gains_compensates(client, arms, config_file):
    arm = arms[1]
    assert arm.gains_are_calibration is True
    assert write(client, Q).status_code == 200
    assert ("write", "P_Coefficient") not in arm.motors_bus.calls


def test_after_another_gain_write_compensation_is_refused_until_torque_on(
    client, arms, config_file, clock, timers
):
    arm, other = arms[1], arms[0]
    start_stream(client, clock)
    # As the gravity loop and the leader-follower do, also when they "restore" gains
    assert arm._try_set_pid_gains_motors(servo_id=2, p_gain=6, i_gain=0, d_gain=9) is True
    assert arm.gains_are_calibration is False and other.gains_are_calibration is True
    refused_for_its_gains(client, arm)
    # An uncompensated write is served as ever
    r = client.post("/joints/write", params=RIGHT, json={"angles": Q, "unit": "rad"})
    assert r.status_code == 200 and goal(arm) == units(arm, Q)
    refused_for_its_gains(client, arm)

    # Torque on writes the calibration's gains on all six servos
    assert client.post("/torque/toggle", params=RIGHT, json=TORQUE_ON).status_code == 200
    assert arm.gains_are_calibration is True
    gains = arm.config.pid_gains
    assert arm.motors_bus.regs["P_Coefficient"] == [int(g.p_gain) for g in gains]
    assert write(client, Q).status_code == 200


def test_the_gravity_loop_leaves_gains_that_are_not_the_calibrations(
    client, arms, config_file, monkeypatch, no_waits
):
    arm = arms[1]
    monkeypatch.setattr(so100, "asyncio", _Asyncio(asyncio))  # its waits return at once
    signal = ControlSignal()  # not started: the loop sets its gains, and restores its own defaults
    asyncio.run(arm.gravity_compensation_loop(signal))
    assert arm.gains_are_calibration is False
    assert arm.motors_bus.regs["P_Coefficient"] != [int(g.p_gain) for g in arm.config.pid_gains]
    refused_for_its_gains(client, arm)
    assert client.post("/torque/toggle", params=RIGHT, json=TORQUE_ON).status_code == 200
    assert write(client, Q).status_code == 200


def test_a_gain_write_that_was_skipped_changes_nothing(arms):
    """With torque off the fork writes no gains (and logs it)."""
    arm = arms[1]
    arm.motors_bus.regs["Torque_Enable"] = [0] * 6
    assert arm._try_set_pid_gains_motors(servo_id=1, p_gain=3, i_gain=0, d_gain=9) is True
    assert ("write", "P_Coefficient") not in arm.motors_bus.calls
    assert arm.gains_are_calibration is True


@pytest.mark.parametrize(
    "setup",
    [
        lambda bus: bus.fail.add("write:D_Coefficient"),  # a gain write fails on the way
        lambda bus: bus.ignore.add("Torque_Enable"),  # torque did not come on: no gains written
    ],
)
def test_a_torque_on_that_did_not_write_all_the_gains_does_not_set_the_flag(
    client, arms, config_file, setup
):
    arm = arms[1]
    arm._try_set_pid_gains_motors(servo_id=2, p_gain=6, i_gain=0, d_gain=9)
    arm.motors_bus.regs["Torque_Enable"] = [0] * 6
    setup(arm.motors_bus)
    assert client.post("/torque/toggle", params=RIGHT, json=TORQUE_ON).status_code == 502
    assert arm.gains_are_calibration is False
    arm.motors_bus.regs["Torque_Enable"] = [1] * 6
    refused_for_its_gains(client, arm)
