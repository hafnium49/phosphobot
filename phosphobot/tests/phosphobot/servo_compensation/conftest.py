"""
Harness of the servo compensation tests: the S1a endpoint harness (two real
SO100Hardware objects whose motors bus is a FakeBus, in a bare FastAPI app) and the
real compensation config file as a fixture.

The guard of tests/phosphobot/conftest.py applies here as everywhere under
tests/phosphobot: no test can open a port or connect to the rig's services.
"""

from pathlib import Path

# The S1a fixtures, made visible to this directory
from s1a.conftest import (  # noqa: F401
    LEFT_SERIAL,
    RIGHT_SERIAL,
    FakeRCM,
    arm_factory,
    arms,
    client,
    client_for,
    hardware_mode,
    only_simulation,
)

CONFIG = Path(__file__).parent / "so101_compensation_v1.json"
