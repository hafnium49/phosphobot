"""
R5 for the remaining movers: teleoperation over WebSocket/UDP selects its arm by a
configured serial, and playback and AI control need named arms.
"""

import pytest
from fastapi import HTTPException

from phosphobot.configs import Configuration, config
from phosphobot.endpoints.control import select_ai_robots
from phosphobot.endpoints.recording import select_playback_robots
from phosphobot.models import AppControlData
from phosphobot.teleoperation import TeleopManager

from .conftest import FakeRCM


@pytest.mark.asyncio
async def test_teleop_without_configured_serial_selects_nothing(arms):
    tm = TeleopManager(rcm=FakeRCM(arms))
    tm._robots = list(arms)
    assert await tm.get_manipulator_robot("right") is None
    assert await tm.get_manipulator_robot("left") is None


@pytest.mark.asyncio
async def test_teleop_selects_by_configured_serial(arms, monkeypatch):
    monkeypatch.setattr(config, "TELEOP_RIGHT_SERIAL", "5A68009540")
    tm = TeleopManager(rcm=FakeRCM(arms))
    tm._robots = list(arms)
    # list position would give arms[0]
    assert await tm.get_manipulator_robot("right") is arms[1]
    assert await tm.get_manipulator_robot("left") is None


@pytest.mark.asyncio
async def test_teleop_selects_nothing_for_a_serial_that_names_no_single_arm(
    arms, monkeypatch
):
    tm = TeleopManager(rcm=FakeRCM(arms))
    tm._robots = list(arms)
    monkeypatch.setattr(config, "TELEOP_RIGHT_SERIAL", "nope")
    assert await tm.get_manipulator_robot("right") is None
    arms[0].SERIAL_ID = arms[1].SERIAL_ID = "no_serial"
    monkeypatch.setattr(config, "TELEOP_RIGHT_SERIAL", "no_serial")
    assert await tm.get_manipulator_robot("right") is None


def test_teleop_serials_load_from_the_config_file(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("teleop_right_serial: 5A68009540\nDEFAULT_FREQ: 20\n")
    loaded = Configuration.from_yaml(path)
    assert loaded.TELEOP_RIGHT_SERIAL == "5A68009540"
    assert loaded.TELEOP_LEFT_SERIAL is None and loaded.DEFAULT_FREQ == 20


def test_playback_and_ai_control_need_named_arms(arms):
    for call in (
        lambda: select_playback_robots(arms, None, None),
        lambda: select_ai_robots(arms, None, None),
    ):
        with pytest.raises(HTTPException) as e:
            call()
        assert e.value.status_code == 422
    assert select_playback_robots(arms, None, ["5A68009540"]) == [arms[1]]
    assert select_playback_robots(arms, 0, None) == [arms[0]]
    assert select_playback_robots(arms, [1, 0], None) == [arms[1], arms[0]]
    both = ["5A68011258", "5A68009540"]
    assert select_ai_robots(arms, both, ["5A68011258"]) == [arms[1]]


def test_selectors_refuse_what_names_no_single_arm(arms):
    for call, code in (
        (lambda: select_playback_robots(arms, None, ["nope"]), 404),
        (lambda: select_ai_robots(arms, ["nope"], None), 404),
        (lambda: select_playback_robots(arms, -1, None), 400),
        (lambda: select_playback_robots(arms, [0, 2], None), 400),
        (lambda: select_playback_robots(arms, None, []), 422),
        (lambda: select_ai_robots(arms, [], None), 422),
        (lambda: select_ai_robots(arms, ["5A68009540"], ["5A68009540"]), 422),
        (lambda: select_ai_robots(arms, ["no_serial"], None), 400),
    ):
        with pytest.raises(HTTPException) as e:
            call()
        assert e.value.status_code == code


def test_playback_refuses_before_loading_an_episode(client):
    r = client.post("/recording/play", json={"episode_path": "/nonexistent"})
    assert r.status_code == 422 and "robot_id or robot_serials" in r.json()["detail"]
    # With an arm named, the request gets as far as the episode
    r = client.post(
        "/recording/play",
        json={"episode_path": "/nonexistent", "robot_serials": ["5A68009540"]},
    )
    assert r.status_code == 400 and "does not exist" in r.json()["detail"]


TELEOP = {"x": 0, "y": 0, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 1}


def test_teleop_initialises_only_the_named_arm(client, arms):
    assert all(a.initial_position is None for a in arms)
    r = client.post("/move/teleop", params={"robot_id": 1}, json=TELEOP)
    assert r.status_code == 200
    assert arms[0].motors_bus.calls == [] and arms[0].initial_position is None
    assert arms[1].initial_position is not None
    assert ("write", "Goal_Position") in arms[1].motors_bus.calls


@pytest.mark.asyncio
async def test_teleop_that_resolves_no_arm_initialises_nothing(arms):
    tm = TeleopManager(rcm=FakeRCM(arms))
    # No robot named, and no serial configured for the controller
    assert await tm.process_control_data(AppControlData(**TELEOP)) is False
    assert all(a.motors_bus.calls == [] and a.initial_position is None for a in arms)


@pytest.mark.asyncio
async def test_teleop_does_not_initialise_an_arm_that_left_the_list(arms):
    # The manager is handed an arm that the connection manager no longer lists
    tm = TeleopManager(rcm=FakeRCM([arms[0]]))
    done = await tm.process_control_data(AppControlData(**TELEOP), robot=arms[1])
    assert done is False
    assert all(a.motors_bus.calls == [] and a.initial_position is None for a in arms)
