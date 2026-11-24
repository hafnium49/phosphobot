"""
The bound of a correction is the server's, not the config file's: no arm joint is
ever written more than 60 motor units (+1 for the truncation) from its request, and
the gripper is written exactly as requested.

- A config file cannot widen the bound, nor bring an arm whose validation failed:
  the runtime refuses the file and the server answers 500.
- Whatever the compensator returns, the server compares the command with the
  request in motor units before the bus write and refuses what is further.
- One sequence of requests is pinned to literal motor units.
"""

import json

import numpy as np
import pytest

from phosphobot import compensated_write
from phosphobot.hardware import servo_compensation as sc

from .conftest import (
    CONFIG,
    DT,
    RIGHT,
    RIGHT_SERIAL,
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


def use_variant(tmp_path, monkeypatch, change):
    cfg = json.loads(CONFIG.read_text())
    change(cfg)
    path = tmp_path / "variant.json"
    path.write_text(json.dumps(cfg))
    monkeypatch.setenv(compensated_write.ENV_VAR, str(path))
    monkeypatch.setattr(compensated_write, "_config", None)


def jump(client, clock):
    """A first request, then 1 rad further on the base 1/15 s later: far over the bound."""
    assert write(client, Q).status_code == 200
    q = list(Q)
    q[0] += 1.0
    clock.advance(DT)
    return q, write(client, q)


def test_the_bound_is_60_ticks():
    assert sc.MAX_TICKS == 60.0


@pytest.mark.parametrize(
    "change,word",
    [
        (lambda c: c.__setitem__("max_ticks", 600), "max_ticks"),
        (lambda c: c.__setitem__("max_ticks", 1e9), "max_ticks"),
        (lambda c: c.__setitem__("max_ticks", -60), "max_ticks"),
        (lambda c: c.__setitem__("max_ticks", 0), "max_ticks"),
        (lambda c: c.__setitem__("max_ticks", 60.5), "max_ticks"),
        (lambda c: c.__setitem__("max_ticks", "60"), "max_ticks"),
        (lambda c: c.__setitem__("max_ticks", True), "max_ticks"),
        (
            lambda c: c["arms"][RIGHT_SERIAL].__setitem__("validation_passed", False),
            "validation",
        ),
        (lambda c: c["arms"][RIGHT_SERIAL].pop("validation_passed"), "validation"),
    ],
)
def test_a_file_that_widens_the_bound_or_failed_validation_is_500(
    client, arms, clock, tmp_path, monkeypatch, change, word
):
    use_variant(tmp_path, monkeypatch, change)
    for arm_params in (RIGHT, {"robot_id": 0}):
        r = write(client, Q, arm=arm_params)
        assert r.status_code == 500 and word in r.json()["detail"], r.text
    assert arms[0].motors_bus.calls == [] and arms[1].motors_bus.calls == []


def test_a_file_may_tighten_the_bound(client, arms, clock, tmp_path, monkeypatch):
    use_variant(tmp_path, monkeypatch, lambda c: c.__setitem__("max_ticks", 20))
    q, r = jump(client, clock)
    assert r.status_code == 200
    assert compensated_write._config.compensators[RIGHT_SERIAL].max_ticks == 20.0
    moved = np.array(goal(arms[1])) - np.array(units(arms[1], q))
    assert abs(moved[0]) == 20 and np.abs(moved[:5]).max() == 20 and moved[5] == 0


def test_with_the_real_config_a_jump_is_written_60_ticks_from_the_request(
    client, arms, config_file, clock
):
    q, r = jump(client, clock)
    assert r.status_code == 200
    moved = (np.array(goal(arms[1])) - np.array(units(arms[1], q))).tolist()
    # The base's sign is -1: +1 rad is 652 units down, and the lag term leads that way
    assert moved[0] == -60 and max(abs(m) for m in moved[:5]) == 60 and moved[5] == 0
    assert r.json()["compensation"]["correction_ticks"] == moved[:5]


def far_command(joint, ticks, gripper_rad=0.0):
    """A compensator whose command is `ticks` motor units off on one joint, whatever the model says."""

    def command(self, q_rad, v_ticks_s, direction, terms=sc.TERMS):
        out = [float(v) for v in q_rad]
        if joint is not None:
            out[joint] += ticks / (self._s[joint] * sc.K)
        out[5] += gripper_rad
        return out

    return command


@pytest.mark.parametrize(
    "joint,ticks,gripper_rad,name",
    [
        (2, 62.5, 0.0, "elbow_flex"),
        (1, -200.0, 0.0, "shoulder_lift"),
        (0, 1000.0, 0.0, "shoulder_pan"),
        (4, -62.5, 0.0, "wrist_roll"),
        (None, 0.0, 1.5 / sc.K, "gripper"),
        (None, 0.0, -0.5, "gripper"),
    ],
)
@pytest.mark.parametrize("terms", ["full", "static"])
def test_the_server_refuses_a_command_beyond_the_bound_whatever_the_compensator_says(
    client, arms, config_file, clock, timers, monkeypatch, joint, ticks, gripper_rad, name, terms
):
    arm = arms[1]
    last = start_stream(client, clock)
    moving, state = goal(arm), arm.servo_compensation
    (timer,) = live(timers)
    far = far_command(joint, ticks, gripper_rad)
    index = 5 if joint is None else joint
    off = units(arm, far(compensator(), Q, None, None))[index] - units(arm, Q)[index]
    assert abs(off) >= (1 if joint is None else 62)
    monkeypatch.setattr(sc.Compensator, "command", far)

    clock.advance(DT)
    r = write(client, Q, terms=terms)
    assert r.status_code == 500, r.text
    # The detail names the joint and how far its command was
    assert name in r.json()["detail"] and f" {off} motor units" in r.json()["detail"]
    # Nothing written, and nothing changed: as for any request refused before the bus
    assert goal_writes(arm) == 2 and goal(arm) == moving
    assert live(timers) == [timer] and state.terms == "full"
    assert state.requested_position == units(arm, last)


def test_the_server_accepts_what_the_truncation_alone_adds(
    client, arms, config_file, clock, monkeypatch
):
    """60 ticks of correction can be 61 motor units once request and command are truncated."""
    arm = arms[1]
    monkeypatch.setattr(sc.Compensator, "command", far_command(2, 60.0))
    seen = set()
    q = list(Q)
    for k in range(40):
        q[2] = Q[2] + k * 0.0004
        r = write(client, q)
        assert r.status_code == 200, r.text
        seen.add(r.json()["compensation"]["correction_ticks"][2])
    assert seen <= {59, 60, 61} and 60 in seen


def test_a_rest_command_beyond_the_bound_is_not_written(
    client, arms, config_file, clock, timers, monkeypatch
):
    arm = arms[1]
    start_stream(client, clock)
    moving = goal(arm)
    monkeypatch.setattr(sc.Compensator, "command", far_command(3, -80.0))
    live(timers)[0].fire()
    assert goal_writes(arm) == 2 and goal(arm) == moving
    assert arm.servo_compensation.terms is None


# The Goal_Position register after each step of run_the_pinned_sequence (see the test)
PINNED = [
    [1917, 1657, 2627, 2305, 1853, 2080],  # first request: the constant and the sag
    [1871, 1631, 2627, 2305, 1853, 2080],  # the line: lag and friction lead on the base and the shoulder lift
    [1858, 1619, 2626, 2305, 1853, 2080],
    [1845, 1606, 2626, 2305, 1853, 2080],
    [1864, 1605, 2626, 2305, 1853, 2080],  # final: no lead
    [1864, 1605, 2626, 2358, 1785, 2080],  # the wrist moves and stops dead: the lead stays
    [1865, 1605, 2626, 2325, 1834, 2080],  # the rest command takes it back
    [1865, 1606, 1922, 2324, 1834, 2080],  # the elbow jumps 1 rad: 60 units from its request, no more
    [1917, 1657, 2627, 2305, 1853, 2080],  # static, back at the first pose
]


def run_the_pinned_sequence(client, arm, clock, timers):
    """One sequence of requests on the right arm; the Goal_Position after each step."""
    seen = []

    def ask(q, **params):
        assert write(client, q, **params).status_code == 200
        seen.append(goal(arm))

    q = list(Q)
    ask(q)  # a first request
    for _ in range(3):  # a line: the base and the shoulder lift at 0.3 rad/s
        q[0] += 0.02
        q[1] -= 0.02
        clock.advance(DT)
        ask(q)
    q[0] += 0.02
    q[1] -= 0.02
    clock.advance(DT)
    ask(q, final=True)  # its last point, named
    q[3] += 0.03
    q[4] -= 0.03
    clock.advance(DT)
    ask(q)  # another move starts and stops dead
    clock.advance(0.1)
    live(timers)[-1].fire()  # the rest command
    seen.append(goal(arm))
    q[2] -= 1.0
    clock.advance(DT)
    ask(q)  # a jump: the bound
    clock.advance(DT)
    ask(Q, terms="static")
    return seen


def test_one_sequence_is_pinned_to_literal_motor_units(
    client, arms, config_file, clock, timers
):
    """
    Not computed from the runtime at test time: these numbers were captured once,
    on 2026-11-24, from a run of this sequence with the runtime of source commit
    f52539c8 and the fixture config, and written here. A change of the model's
    equation, of the stream's logic or of the fork's conversion shows as a diff.
    """
    seen = run_the_pinned_sequence(client, arms[1], clock, timers)
    assert seen == PINNED
