"""
The operator's STOP. On this rig STOP is a file on the clients' side: while it
exists, nothing may move. Clients check it before every write; the server's rest
timer is the one writer they cannot hold back. So the server watches the files of
PHOSPHOBOT_STOP_FILES: while one exists the rest timer writes nothing, and a
compensated write is refused 423. Uncompensated writes and every other endpoint are
as before.
"""

import errno
import os
from pathlib import Path

import pytest
from loguru import logger

from phosphobot import compensated_write

from .conftest import DT, RIGHT, Q, goal, goal_writes, start_stream, units, write
from .test_default_path import BASE_RESPONSE, BASE_UNITS_RAD
from .test_goal_register import fire_and_listen
from .test_refused_request import raw, rest_units, state_of

SERIAL = RIGHT["serial"]
NOT_CONFIGURED = "no STOP file is configured: the rest timer cannot honour a STOP"
GOAL_WRITE = ("write", "Goal_Position")


def live(timers):
    return [timer for timer in timers if not timer.cancelled]


def listen(action):
    """What `action` returns, and everything the server logged meanwhile."""
    logged = []
    sink = logger.add(logged.append, level="INFO")
    try:
        result = action()
    finally:
        logger.remove(sink)
    return result, "".join(str(message) for message in logged)


@pytest.fixture
def watched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list:
    """The server was started watching two STOP files. Neither exists yet."""
    paths = [tmp_path / "bench_STOP.json", tmp_path / "claude_hands_STOP.json"]
    monkeypatch.setenv(
        compensated_write.STOP_ENV_VAR, os.pathsep.join(str(path) for path in paths)
    )
    return paths


@pytest.fixture
def stop_file(watched: list) -> Path:
    return watched[1]


def test_with_no_stop_file_present_everything_is_as_without_the_variable(
    client, arms, config_file, stop_file, clock, timers
):
    arm = arms[1]
    last = start_stream(client, clock)
    logged = fire_and_listen(live(timers)[0])
    assert goal_writes(arm) == 3 and goal(arm) == rest_units(arm, last) and logged == ""
    assert raw(client) == (units(arm, last), "full")


def test_the_response_says_how_many_stop_files_are_watched(
    client, arms, config_file, watched
):
    r, logged = listen(lambda: write(client, Q))
    assert r.status_code == 200 and r.json()["compensation"]["stop_files"] == 2
    # Read with the compensation config, and said once
    assert f"STOP files watched: {[str(path) for path in watched]}" in logged
    assert NOT_CONFIGURED not in logged
    r, logged = listen(lambda: write(client, Q, terms="static", final=True))
    assert r.json()["compensation"]["stop_files"] == 2 and "STOP file" not in logged


@pytest.mark.parametrize("value", [None, "", os.pathsep, f" {os.pathsep} "])
def test_without_the_variable_no_stop_file_is_watched_and_the_server_says_so(
    client, arms, config_file, clock, timers, monkeypatch, tmp_path, value
):
    """Today's behaviour, and a client can see it: "stop_files" is 0."""
    arm = arms[1]
    if value is not None:
        monkeypatch.setenv(compensated_write.STOP_ENV_VAR, value)
    r, logged = listen(lambda: write(client, Q))
    assert r.status_code == 200 and r.json()["compensation"]["stop_files"] == 0
    assert logged.count(NOT_CONFIGURED) == 1 and "WARNING" in logged
    arm.servo_compensation.void()
    last, logged = listen(lambda: start_stream(client, clock))
    assert NOT_CONFIGURED not in logged
    live(timers)[0].fire()
    assert goal_writes(arm) == 4 and goal(arm) == rest_units(arm, last)


@pytest.mark.parametrize("which", [0, 1])
def test_a_stop_after_the_last_write_holds_back_the_rest_command(
    client, arms, config_file, watched, clock, timers, which
):
    arm = arms[1]
    start_stream(client, clock)
    moving = goal(arm)
    watched[which].write_text('{"reason": "operator"}')
    calls = len(arm.motors_bus.calls)
    logged = fire_and_listen(live(timers)[0])
    assert GOAL_WRITE not in arm.motors_bus.calls[calls:]
    assert goal_writes(arm) == 2 and goal(arm) == moving
    assert (
        f"STOP file {watched[which]} present: the rest command of arm {SERIAL} was not written"
        in logged
    )
    # Void, as after the timer's other refusals: the raw read says so
    state = arm.servo_compensation
    assert state.terms is None and all(s._q is None for s in state.streams.values())
    assert raw(client) == (None, None)
    # Nothing comes later either, also once the STOP is cleared
    watched[which].unlink()
    for timer in timers:
        timer.fire()
    assert goal_writes(arm) == 2


@pytest.mark.parametrize("during", ["Torque_Enable", "Goal_Position"])
def test_a_stop_that_appears_during_the_timers_own_reads_is_honoured(
    client, arms, config_file, stop_file, clock, timers, during
):
    """The check is the last thing before the write, after the bus reads."""
    arm = arms[1]
    start_stream(client, clock)
    moving, bus = goal(arm), arm.motors_bus
    real_read, real_read_by_id = bus.read, bus.read_with_motor_ids

    def read(data_name, motor_names=None):
        if data_name == during:
            stop_file.write_text("{}")
        return real_read(data_name, motor_names)

    def read_by_id(motor_models, motor_ids, data_name, **kwargs):
        if data_name == during:
            stop_file.write_text("{}")
        return real_read_by_id(motor_models, motor_ids, data_name, **kwargs)

    bus.read, bus.read_with_motor_ids = read, read_by_id
    assert not stop_file.exists()
    logged = fire_and_listen(live(timers)[0])
    assert stop_file.exists()
    assert goal_writes(arm) == 2 and goal(arm) == moving
    assert f"STOP file {stop_file} present" in logged
    assert arm.servo_compensation.terms is None


@pytest.mark.parametrize(
    "terms,final", [("full", None), ("full", True), ("static", None), ("static", True)]
)
def test_a_compensated_write_is_423_while_a_stop_file_is_present_and_changes_nothing(
    client, arms, config_file, stop_file, clock, timers, terms, final
):
    arm = arms[1]
    last = start_stream(client, clock)
    moving, state = goal(arm), arm.servo_compensation
    stream = state.streams["full"]
    before = state_of(stream)
    (timer,) = live(timers)

    stop_file.write_text("{}")
    calls = list(arm.motors_bus.calls)
    q = list(last)
    q[1] -= 0.02
    clock.advance(DT)
    r = write(client, q, terms=terms, final=final)
    assert r.status_code == 423, r.text
    assert r.json()["detail"] == f"STOP file {stop_file} is present: nothing was written"
    # Nothing reached the bus, and nothing changed: as for any request refused before it
    assert arm.motors_bus.calls == calls and goal(arm) == moving
    assert live(timers) == [timer] and len(timers) == 1
    assert state_of(stream) == before and state.streams == {"full": stream}
    assert raw(client) == (units(arm, last), "full")

    # The timer of the request before is still pending. It fires: the STOP holds it back
    logged = fire_and_listen(timer)
    assert goal_writes(arm) == 2 and goal(arm) == moving
    assert f"STOP file {stop_file} present: the rest command of arm {SERIAL}" in logged
    assert raw(client) == (None, None)


def test_a_first_compensated_write_under_a_stop_leaves_no_state(
    client, arms, config_file, stop_file
):
    arm = arms[1]
    stop_file.write_text("{}")
    assert write(client, Q).status_code == 423
    assert arm.motors_bus.calls == []
    state = arm.servo_compensation
    assert state is None or (state.streams == {} and state.terms is None)


def test_when_the_stop_is_cleared_the_stream_goes_on(
    client, arms, config_file, stop_file, clock, timers
):
    arm = arms[1]
    last = start_stream(client, clock)
    stop_file.write_text("{}")
    clock.advance(DT)
    assert write(client, last).status_code == 423
    stop_file.unlink()
    q = list(last)
    q[1] -= 0.02
    r = write(client, q)
    assert r.status_code == 200 and goal_writes(arm) == 3
    assert arm.servo_compensation.requested_position == units(arm, q)
    assert len(live(timers)) == 1 and timers[0].cancelled


def test_an_uncompensated_write_and_the_other_endpoints_are_not_held_by_a_stop(
    client, arms, config_file, stop_file
):
    arm = arms[1]
    assert write(client, Q).status_code == 200  # the STOP files are loaded
    stop_file.write_text("{}")
    r = client.post("/joints/write", params={"robot_id": 1}, json={"angles": Q, "unit": "rad"})
    assert (r.status_code, r.content) == (200, BASE_RESPONSE)
    assert goal(arm) == BASE_UNITS_RAD and goal_writes(arm) == 2
    for path, body in (
        ("/joints/read", None),
        ("/joints/read/raw", None),
        ("/torque/toggle", {"torque_status": False}),
        ("/torque/toggle", {"torque_status": True}),
    ):
        assert client.post(path, params=RIGHT, json=body).status_code == 200, path


def check_counts_as_present(client, arm, clock, timers, path, make_unreadable):
    """A watched path that cannot be checked holds back the timer and the write."""
    last = start_stream(client, clock)
    moving = goal(arm)
    (timer,) = live(timers)
    make_unreadable()
    r, logged = listen(lambda: write(client, last))
    assert r.status_code == 423, r.text
    detail = r.json()["detail"]
    assert detail.startswith(f"STOP file {path} cannot be checked (")
    assert detail.endswith("and counts as present: nothing was written")
    assert f"STOP file {path} cannot be checked" in logged and "WARNING" in logged
    assert goal_writes(arm) == 2 and live(timers) == [timer]
    logged = fire_and_listen(timer)
    assert goal_writes(arm) == 2 and goal(arm) == moving
    assert f"STOP file {path} cannot be checked" in logged
    assert f"the rest command of arm {SERIAL} was not written" in logged
    assert arm.servo_compensation.terms is None


@pytest.mark.skipif(os.geteuid() == 0, reason="root can stat anything")
def test_a_stop_file_in_a_directory_that_cannot_be_searched_counts_as_present(
    client, arms, config_file, clock, timers, tmp_path, monkeypatch
):
    locked = tmp_path / "locked"
    locked.mkdir()
    path = locked / "STOP.json"  # it does not exist; nobody can tell
    monkeypatch.setenv(compensated_write.STOP_ENV_VAR, str(path))
    try:
        check_counts_as_present(
            client, arms[1], clock, timers, path, lambda: locked.chmod(0o000)
        )
    finally:
        locked.chmod(0o700)


@pytest.mark.parametrize(
    "error",
    [OSError(errno.EIO, "Input/output error"), NotADirectoryError(errno.ENOTDIR, "Not a directory")],
)
def test_a_stop_file_whose_check_fails_for_another_reason_than_absence_counts_as_present(
    client, arms, config_file, stop_file, clock, timers, monkeypatch, error
):
    real_lstat = os.lstat

    def lstat(path, *args, **kwargs):
        if str(path) == str(stop_file):
            raise error
        return real_lstat(path, *args, **kwargs)

    check_counts_as_present(
        client,
        arms[1],
        clock,
        timers,
        stop_file,
        lambda: monkeypatch.setattr(compensated_write.os, "lstat", lstat),
    )


def test_a_dangling_link_is_a_stop_file_too(client, arms, config_file, stop_file, tmp_path):
    """The directory entry exists: the server does not ask what it points to."""
    stop_file.symlink_to(tmp_path / "nowhere")
    assert not stop_file.exists()
    assert write(client, Q).status_code == 423 and arms[1].motors_bus.calls == []
