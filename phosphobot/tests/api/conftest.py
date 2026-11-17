"""
The tests of this directory are skipped unless PHOSPHOBOT_API_TESTS_LIVE=1.

They are not self-contained: they send HTTP, WebSocket and UDP to the phosphobot
server on 127.0.0.1:8080, whatever server that is, and they move robot 0, start
recordings and write ~/phosphobot/huggingface.token. On a machine wired to real
arms that server drives the arms.

Run them only against a server started for them (`make test_server`):

    PHOSPHOBOT_API_TESTS_LIVE=1 uv run pytest tests/api
"""

import os
from pathlib import Path

import pytest

OPT_IN = "PHOSPHOBOT_API_TESTS_LIVE"
REASON = (
    "tests/api drives the live phosphobot server on 127.0.0.1:8080 and moves robot 0;"
    f" set {OPT_IN}=1 to run it"
)
HERE = Path(__file__).parent.resolve()


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    if os.environ.get(OPT_IN) == "1":
        return
    skip = pytest.mark.skip(reason=REASON)
    for item in items:
        # This hook sees every test of the session, not only those of this directory
        if HERE in Path(str(item.fspath)).resolve().parents:
            item.add_marker(skip)
