"""Shared fixtures for RLPaperDrag test suite.

Resolves asset paths and cross-repo imports. Tests skip gracefully if the
required checkpoint / YOLO weights / NPZ / calibration assets are not present
on the host (so this file is safe in CI on a machine without the 90 MB of
model bundles).

Environment variables:
    SO101_ASSETS_DIR   (default: /home/hafnium/so101-rl-deploy/models)
        Directory containing best_run20_98pct.pt + paper_yolo_obb.pt
    SO101_RL_DEPLOY_DIR   (default: /home/hafnium/so101-rl-deploy)
        Directory containing:
            assets/motions/so101_nmpc_references.npz
            calibration.json
            rl_policy_controller.py   (for parity tests)

The second env var's path is also inserted into sys.path so the parity
test can import RLPolicyController directly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

# --- Cross-repo import resolution (for parity tests that compare against
#     RLPolicyController from so101-rl-deploy) ---
SO101_RL_DEPLOY = os.environ.get("SO101_RL_DEPLOY_DIR", "/home/hafnium/so101-rl-deploy")
if Path(SO101_RL_DEPLOY).is_dir() and SO101_RL_DEPLOY not in sys.path:
    sys.path.insert(0, SO101_RL_DEPLOY)

# --- Asset directory (weights) ---
_DEFAULT_ASSETS_DIR = "/home/hafnium/so101-rl-deploy/models"
ASSETS_DIR = Path(os.environ.get("SO101_ASSETS_DIR", _DEFAULT_ASSETS_DIR))


def _required_asset_paths():
    return {
        "checkpoint": ASSETS_DIR / "best_run20_98pct.pt",
        "yolo_weights": ASSETS_DIR / "paper_yolo_obb.pt",
        "reference_npz": Path(SO101_RL_DEPLOY) / "assets" / "motions" / "so101_nmpc_references.npz",
        "calibration": Path(SO101_RL_DEPLOY) / "calibration.json",
    }


def _missing_assets() -> list[str]:
    return [name for name, p in _required_asset_paths().items() if not p.exists()]


# -------- Shared fixtures --------

@pytest.fixture(scope="session")
def assets_available() -> bool:
    """True if all 4 required assets exist; else tests should skip."""
    return not _missing_assets()


@pytest.fixture(scope="session")
def skip_if_no_assets(assets_available):
    """Call this at the top of a test to auto-skip when assets are absent.

    Usage:
        def test_foo(skip_if_no_assets, ...):
            ...
    """
    if not assets_available:
        missing = _missing_assets()
        pytest.skip(
            f"Skipping RLPaperDrag asset-dependent test. Missing: {missing}. "
            f"Set SO101_ASSETS_DIR and SO101_RL_DEPLOY_DIR env vars, or ensure "
            f"defaults at {ASSETS_DIR} and {SO101_RL_DEPLOY} are populated."
        )


@pytest.fixture(scope="session")
def rl_assets_bundle(tmp_path_factory, skip_if_no_assets):
    """Return a Path to a tmpdir containing all 4 required assets (via symlinks).

    fetch_and_verify_config expects a single directory with all 4 files
    co-located with canonical names. Our assets live in two different
    source dirs, so we build a unified bundle via symlinks.
    """
    paths = _required_asset_paths()
    bundle = tmp_path_factory.mktemp("rl_paper_drag_assets")
    # fetch_and_verify_config expects these exact filenames
    (bundle / "best_run20_98pct.pt").symlink_to(paths["checkpoint"].resolve())
    (bundle / "paper_yolo_obb.pt").symlink_to(paths["yolo_weights"].resolve())
    (bundle / "so101_nmpc_references.npz").symlink_to(paths["reference_npz"].resolve())
    (bundle / "calibration.json").symlink_to(paths["calibration"].resolve())
    return bundle


@pytest.fixture(scope="session")
def spawn_config(rl_assets_bundle):
    """Return a pre-built RLPaperDragSpawnConfig pointing at the asset bundle.

    Tests that need the full config (e.g. instantiation) use this.
    Detection PUB port disabled (None) to avoid cross-test port collisions.
    """
    from phosphobot.am.rl_paper_drag import RLPaperDragSpawnConfig
    return RLPaperDragSpawnConfig(
        model_dir=str(rl_assets_bundle),
        checkpoint_path=str(rl_assets_bundle / "best_run20_98pct.pt"),
        yolo_model_path=str(rl_assets_bundle / "paper_yolo_obb.pt"),
        reference_npz_path=str(rl_assets_bundle / "so101_nmpc_references.npz"),
        calibration_json_path=str(rl_assets_bundle / "calibration.json"),
        publish_detections_port=None,
        device="cpu",
    )


@pytest.fixture(scope="function")
def rl_paper_drag(spawn_config):
    """Return a fresh RLPaperDrag instance per test (isolates per-episode state)."""
    from phosphobot.am.rl_paper_drag import RLPaperDrag
    return RLPaperDrag(spawn_config)


# -------- Mock hardware backends (no USB / real servos needed) --------

class MockManipulator:
    """Minimal BaseManipulator stub for testing control_loop without real servos.

    Tracks:
        reads_unit: list of unit kwargs passed to read_joints_position
        writes:    list of (angles, unit) tuples passed to write_joint_positions
        joint_pos: current joint state (6,), mutated by write calls so reads
                   reflect the last commanded position (zero-order-hold model)
    """
    def __init__(self, initial_joints: np.ndarray | None = None):
        self.joint_pos = (
            np.asarray(initial_joints, dtype=float).copy()
            if initial_joints is not None
            else np.zeros(6)
        )
        self.reads_unit: list[str] = []
        self.writes: list[tuple[list[float], str]] = []
        self.read_call_count = 0
        self.write_call_count = 0

    def read_joints_position(self, unit: str = "rad", **kwargs):
        self.reads_unit.append(unit)
        self.read_call_count += 1
        # Return in radians always (matches real hardware API), convert if asked
        if unit == "rad":
            return self.joint_pos.tolist()
        elif unit == "degrees":
            return np.degrees(self.joint_pos).tolist()
        return self.joint_pos.tolist()

    def write_joint_positions(self, angles, unit="rad", **kwargs):
        self.writes.append((list(angles), unit))
        self.write_call_count += 1
        # Update internal state so next read reflects the write
        angles_arr = np.asarray(angles, dtype=float)
        if unit == "degrees":
            self.joint_pos = np.radians(angles_arr)
        else:
            self.joint_pos = angles_arr


class MockAllCameras:
    """Minimal AllCameras stub. get_rgb_frame returns a canned frame.

    By default returns a 360x640x3 black frame (uint8). Tests can override
    via .set_frame() or .set_frame_provider(callable) for dynamic behavior.
    """
    def __init__(self, w: int = 640, h: int = 360):
        self._w, self._h = w, h
        self._frame: np.ndarray | None = None
        self._provider = None
        self.get_frame_call_count = 0

    def set_frame(self, frame: np.ndarray):
        self._frame = frame

    def set_frame_provider(self, fn):
        """fn(call_count) -> np.ndarray | None"""
        self._provider = fn

    def get_rgb_frame(self, camera_id: int = 0, resize=None):
        self.get_frame_call_count += 1
        if self._provider is not None:
            return self._provider(self.get_frame_call_count)
        if self._frame is not None:
            return self._frame
        # Default: black frame (RGB)
        return np.zeros((self._h, self._w, 3), dtype=np.uint8)


class MockControlSignal:
    """Minimal AIControlSignal stub. Counts iterations then stops.

    Supports two modes:
        - `stop_after_n=N`: loop runs N iterations then returns False from is_in_loop
        - `external_stop()`: manually stop the loop from a test
    """
    def __init__(self, stop_after_n: int | None = None):
        self._running = True
        self._iter_count = 0
        self._stop_after_n = stop_after_n
        self._started = False

    def is_in_loop(self) -> bool:
        self._iter_count += 1
        if self._stop_after_n is not None and self._iter_count > self._stop_after_n:
            return False
        return self._running

    def set_running(self):
        self._started = True

    def stop(self):
        self._running = False

    def external_stop(self):
        self._running = False


@pytest.fixture
def mock_manipulator():
    return MockManipulator(initial_joints=np.zeros(6))


@pytest.fixture
def mock_all_cameras():
    return MockAllCameras()


@pytest.fixture
def mock_control_signal():
    """Default: auto-stops after 5 iterations."""
    return MockControlSignal(stop_after_n=5)
