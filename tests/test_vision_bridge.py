import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import io
import importlib
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient


def load_vb_module():
    with patch('prometheus_client.start_http_server', lambda *a, **k: None):
        return importlib.import_module('vision_bridge.main')


@pytest.fixture
def vb_app():
    return load_vb_module()


def test_color_checker_invalid_image(vb_app):
    client = TestClient(vb_app.app)
    response = client.post('/color-checker', files={'file': ('bad.txt', b'invalid', 'text/plain')})
    assert response.status_code == 400


def test_snapshot_upload(vb_app):
    class DummyResponse:
        def __init__(self):
            self.status_code = 200
            self.content = b'jpgdata'
        def json(self):
            return {}
    class DummyClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def get(self, url, timeout):
            return DummyResponse()
    class DummyS3:
        def upload_fileobj(self, data, bucket, key, ExtraArgs=None):
            assert bucket == vb_app.BUCKET
        def generate_presigned_url(self, *a, **k):
            return 'http://example.com'
    with patch.object(vb_app, 'httpx', vb_app.httpx), \
         patch.object(vb_app.httpx, 'AsyncClient', lambda *a, **k: DummyClient()), \
         patch.object(vb_app, 's3', DummyS3()):
        client = TestClient(vb_app.app)
        payload = {'cmd_id': '1', 'cam_id': 'c'}
        resp = client.post('/snapshot', json=payload)
        assert resp.status_code == 200
        assert resp.json()['url'] == 'http://example.com'
