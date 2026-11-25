"""
The runtime of the servo compensation is a verbatim copy of a file of another repository
(see the header of phosphobot/hardware/servo_compensation.py). These tests make a drift
of the copy, or of the fork's own conversion that it relies on, visible.
"""

import ast
import hashlib
from pathlib import Path

import numpy as np

import phosphobot
from phosphobot.hardware import SO100Hardware

RUNTIME = Path(phosphobot.__file__).parent / "hardware" / "servo_compensation.py"
SOURCE_SHA256 = "c90036bd1087b6977a4e0f23c7aad64e7489fbbc84703a37a25cf97abf940ec5"
CONFIG = Path(__file__).parent / "so101_compensation_v1.json"
CONFIG_SHA256 = "5dc6de5463deafc9564682f294c08b5405eb1dd3771484327a51073d2f0a0b57"
# Version 2 of the config: version 1 with the friction values of two left-arm joints
# changed, and three more top-level keys (derived_from, changes, changes_note)
CONFIG_V2 = Path(__file__).parent / "so101_compensation_v2.json"
CONFIG_V2_SHA256 = "356e00872d304c5780b31cf4713a2aa3202b4c151a34ca20eac59b6b9a28d69b"
END_OF_HEADER = b"# ----- END OF HEADER -----\n"


def test_the_body_of_the_copy_is_the_source_file():
    header, marker, body = RUNTIME.read_bytes().partition(END_OF_HEADER)
    assert marker == END_OF_HEADER
    # sha256 of the source file, as sha256sum prints it
    assert hashlib.sha256(body).hexdigest() == SOURCE_SHA256
    # The header is comments only, and names what the body is a copy of
    assert all(line.startswith(b"#") for line in header.splitlines())
    assert SOURCE_SHA256.encode() in header
    assert b"cfaa8cc3fa5909df0248a03f85175d43df66f6c4" in header


def test_the_fixture_config_is_the_real_one():
    assert hashlib.sha256(CONFIG.read_bytes()).hexdigest() == CONFIG_SHA256
    assert hashlib.sha256(CONFIG_V2.read_bytes()).hexdigest() == CONFIG_V2_SHA256


def test_the_copy_needs_numpy_and_the_standard_library_only():
    tree = ast.parse(RUNTIME.read_text())
    top = {n.names[0].name.split(".")[0] for n in tree.body if isinstance(n, ast.Import)}
    top |= {
        n.module.split(".")[0]
        for n in tree.body
        if isinstance(n, ast.ImportFrom) and n.module
    }
    assert top <= {"__future__", "json", "time", "pathlib", "typing", "numpy", "hashlib"}


def test_the_copy_and_the_fork_agree_on_ticks_and_joints():
    from phosphobot.hardware import servo_compensation as sc

    # BaseManipulator._radians_vec_to_motor_units: radians * (RESOLUTION - 1) / (2 pi)
    assert sc.K == (SO100Hardware.RESOLUTION - 1) / (2 * np.pi)
    assert list(SO100Hardware.motors)[:5] == list(sc.JOINTS)
    assert list(SO100Hardware.motors)[5] == "gripper"


def test_the_config_loads_with_numpy_alone_and_says_something():
    from phosphobot.hardware import servo_compensation as sc

    comp = sc.Compensator.from_config(CONFIG, "5A68009540")
    reach = [0.0] * 6
    out = comp.command(reach, np.zeros(5), np.zeros(5), sc.STATIC)
    # The arm reaches forward: the shoulder lift is asked to go several ticks further
    assert abs(out[1] - reach[1]) * sc.K > 5.0 and out[5] == reach[5]


def test_the_server_loads_version_2_of_the_config_as_it_loads_version_1(
    client, arms, monkeypatch
):
    """Same schema; the keys the server does not know are ignored."""
    import json

    from phosphobot import compensated_write

    from .conftest import LEFT, LEFT_SERIAL, RIGHT_SERIAL, Q, goal, units, write

    v1, v2 = json.loads(CONFIG.read_text()), json.loads(CONFIG_V2.read_text())
    assert v2["schema"] == v1["schema"] == 1
    assert set(v2) - set(v1) == {"derived_from", "changes", "changes_note"}
    monkeypatch.setenv(compensated_write.ENV_VAR, str(CONFIG_V2))
    for arm_params in (LEFT, {"serial": RIGHT_SERIAL}):
        r = write(client, Q, arm=arm_params)
        assert r.status_code == 200, r.text
    loaded = compensated_write._config.compensators
    assert sorted(loaded) == sorted([LEFT_SERIAL, RIGHT_SERIAL])
    left = loaded[LEFT_SERIAL].params
    assert left["shoulder_lift"]["psi0"] == 2.2 and left["shoulder_lift"]["psic"] == 1.3
    assert left["elbow_flex"]["psi0"] == 2.0
    # Everything else is version 1: the right arm, and a first request (no friction yet)
    assert loaded[RIGHT_SERIAL].params == v1["arms"][RIGHT_SERIAL]["params"]
    from phosphobot.hardware import servo_compensation as sc

    first = sc.Compensator.from_config(CONFIG, LEFT_SERIAL).command(Q, np.zeros(5), np.zeros(5))
    assert goal(arms[0]) == units(arms[0], first)
