import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# Utility to import module with patched environment

def load_robot_module():
    def fake_create_task(coro):
        coro.close()
        loop = asyncio.new_event_loop()
        return loop.create_future()

    with patch('asyncio.create_task', fake_create_task), \
         patch('prometheus_client.start_http_server', lambda *a, **k: None), \
         patch('prometheus_client.Histogram.time', lambda self: (lambda f: f)):
        return importlib.import_module('robot_service.main')


@pytest.fixture
def robot_app():
    mod = load_robot_module()
    return mod


def test_pose_close_match(robot_app):
    robot_app.TARGET_POSE = [0.0, 0.0]
    robot_app.TOL = 0.1
    assert robot_app.pose_close([0.05, 0.05])
    assert not robot_app.pose_close([0.2, 0.0])


def test_dispense_and_status(robot_app):
    class DummyResponse:
        def __init__(self):
            self.status_code = 200
        def json(self):
            return {'predicted_squeeze_sec': 1.23}

    class DummyClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def post(self, url, json):
            return DummyResponse()

    with patch.object(robot_app.httpx, 'AsyncClient', lambda *a, **k: DummyClient()), \
         patch.object(robot_app.uuid, 'uuid4', lambda: 'abc'):
        client = TestClient(robot_app.app)
        payload = {'mix_id': 1, 'run_id': 2, 'colour': 'red', 'volume_ml': 10.0}
        resp = client.post('/robot/dispense', json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data['cmd_id'] == 'abc'
        assert data['predicted_squeeze_sec'] == 1.23

        status = client.get(f"/robot/{data['cmd_id']}/status")
        assert status.status_code == 200
        assert status.json()['status'] == 'running'
        assert status.json()['predicted_squeeze_sec'] == 1.23
