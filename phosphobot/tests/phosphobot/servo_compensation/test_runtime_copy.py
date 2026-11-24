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
SOURCE_SHA256 = "dbd4001182cee1b25eb371d71bf20f112e68eb69196b2cf3be3c98f34ea02f5a"
CONFIG = Path(__file__).parent / "so101_compensation_v1.json"
CONFIG_SHA256 = "5dc6de5463deafc9564682f294c08b5405eb1dd3771484327a51073d2f0a0b57"
END_OF_HEADER = b"# ----- END OF HEADER -----\n"


def test_the_body_of_the_copy_is_the_source_file():
    header, marker, body = RUNTIME.read_bytes().partition(END_OF_HEADER)
    assert marker == END_OF_HEADER
    # sha256 of the source file, as sha256sum prints it
    assert hashlib.sha256(body).hexdigest() == SOURCE_SHA256
    # The header is comments only, and names what the body is a copy of
    assert all(line.startswith(b"#") for line in header.splitlines())
    assert SOURCE_SHA256.encode() in header
    assert b"1640db5c14614f815d407c5fa6f8b6d22eba9535" in header


def test_the_fixture_config_is_the_real_one():
    assert hashlib.sha256(CONFIG.read_bytes()).hexdigest() == CONFIG_SHA256


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
