import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from unittest.mock import patch
import importlib


def load_app():
    with patch('prometheus_client.start_http_server', lambda *a, **k: None):
        mod = importlib.import_module('vision_bridge.main')
    return mod.app


def test_color_checker_sample():
    app = load_app()
    client = TestClient(app)
    with open('vision_bridge/samples/ColorCheckerClassic_24patch_sRGB.png', 'rb') as f:
        resp = client.post('/color-checker', files={'file': ('img.png', f, 'image/png')})
    assert resp.status_code == 200

