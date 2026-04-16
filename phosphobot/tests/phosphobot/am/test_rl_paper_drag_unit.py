"""Unit tests for RLPaperDrag internals.

Covers:
    - _ActorMLP architecture + checkpoint loading
    - _ObsNormalizer buffers + shapes
    - _wrap_angle correctness
    - RLPaperDrag._match_reference determinism
    - RLPaperDrag.sample_actions output shape/range (noise off)
    - fetch_and_verify_config error paths (parametrized over missing file)
    - fetch_and_verify_config invalid model_id (non-dir)
    - fetch_and_verify_config wrong robot count

All tests skip cleanly if assets are missing (see conftest.py).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


# -------- _wrap_angle (pure function, no assets needed) --------

def test_wrap_angle_basic():
    from phosphobot.am.rl_paper_drag import _wrap_angle
    assert _wrap_angle(0.0) == pytest.approx(0.0)
    assert _wrap_angle(np.pi) == pytest.approx(np.pi, abs=1e-10) or \
           _wrap_angle(np.pi) == pytest.approx(-np.pi, abs=1e-10)
    assert _wrap_angle(-np.pi) == pytest.approx(-np.pi, abs=1e-10) or \
           _wrap_angle(-np.pi) == pytest.approx(np.pi, abs=1e-10)
    assert _wrap_angle(2 * np.pi) == pytest.approx(0.0, abs=1e-10)
    assert _wrap_angle(-3 * np.pi) == pytest.approx(np.pi, abs=1e-10) or \
           _wrap_angle(-3 * np.pi) == pytest.approx(-np.pi, abs=1e-10)


def test_wrap_angle_near_boundary():
    from phosphobot.am.rl_paper_drag import _wrap_angle
    eps = 1e-6
    assert _wrap_angle(np.pi - eps) == pytest.approx(np.pi - eps, abs=1e-9)
    assert _wrap_angle(np.pi + eps) == pytest.approx(-(np.pi - eps), abs=1e-9)


# -------- _ActorMLP structure + checkpoint load --------

def test_actor_mlp_structure():
    from phosphobot.am.rl_paper_drag import _ActorMLP
    import torch

    net = _ActorMLP(obs_dim=1650, act_dim=6, hidden_dims=[512, 256, 128])
    linears = [m for m in net.mlp if isinstance(m, torch.nn.Linear)]
    assert len(linears) == 4
    assert linears[0].in_features == 1650 and linears[0].out_features == 512
    assert linears[1].in_features == 512 and linears[1].out_features == 256
    assert linears[2].in_features == 256 and linears[2].out_features == 128
    assert linears[3].in_features == 128 and linears[3].out_features == 6
    assert net.std.shape == (6,)


def test_actor_mlp_forward_finite():
    from phosphobot.am.rl_paper_drag import _ActorMLP
    import torch

    net = _ActorMLP(1650, 6, [512, 256, 128]).eval()
    with torch.inference_mode():
        out = net(torch.zeros(1, 1650))
    assert out.shape == (1, 6)
    assert torch.isfinite(out).all()


def test_actor_mlp_loads_run20_checkpoint(rl_assets_bundle):
    """Run #20 checkpoint loads strictly into _ActorMLP + _ObsNormalizer."""
    from phosphobot.am.rl_paper_drag import _ActorMLP, _ObsNormalizer
    import torch

    ckpt = torch.load(
        str(rl_assets_bundle / "best_run20_98pct.pt"),
        map_location="cpu",
        weights_only=False,
    )
    actor_sd = ckpt["actor_state_dict"]

    norm_sd = {k.replace("obs_normalizer.", ""): v for k, v in actor_sd.items()
               if k.startswith("obs_normalizer.")}
    mlp_sd = {k: v for k, v in actor_sd.items()
              if k.startswith("mlp.") or k == "std"}

    normalizer = _ObsNormalizer(1650)
    actor = _ActorMLP(1650, 6, [512, 256, 128])
    # Must load strictly — any key drift = port bug.
    normalizer.load_state_dict(norm_sd, strict=True)
    actor.load_state_dict(mlp_sd, strict=True)

    with torch.inference_mode():
        out = actor(normalizer(torch.zeros(1, 1650)))
    assert out.shape == (1, 6)
    assert torch.isfinite(out).all()


# -------- _ObsNormalizer --------

def test_obs_normalizer_default_buffers():
    from phosphobot.am.rl_paper_drag import _ObsNormalizer
    import torch

    n = _ObsNormalizer(1650)
    assert n._mean.shape == (1, 1650)
    assert n._std.shape == (1, 1650)
    assert n._var.shape == (1, 1650)
    assert int(n.count.item()) == 0
    # Default pass-through: mean=0, std=1 → x/(1+eps) ≈ x
    with torch.inference_mode():
        x = torch.randn(1, 1650)
        y = n(x)
    assert torch.allclose(y, x / (1.0 + n.eps), atol=1e-6)


def test_obs_normalizer_loads_run20_stats(rl_assets_bundle):
    from phosphobot.am.rl_paper_drag import _ObsNormalizer
    import torch

    ckpt = torch.load(
        str(rl_assets_bundle / "best_run20_98pct.pt"),
        map_location="cpu",
        weights_only=False,
    )
    norm_sd = {k.replace("obs_normalizer.", ""): v
               for k, v in ckpt["actor_state_dict"].items()
               if k.startswith("obs_normalizer.")}
    n = _ObsNormalizer(1650)
    n.load_state_dict(norm_sd, strict=True)

    assert n._mean.shape == (1, 1650)
    assert n._std.shape == (1, 1650)
    assert float(n._std.min()) > 0, "std must be strictly positive (no div-by-zero)"
    assert int(n.count.item()) > 0, "normalizer must have been fit during training"


def test_obs_normalizer_handles_nan():
    """NaNs in input should not propagate (forward uses nan_to_num)."""
    from phosphobot.am.rl_paper_drag import _ObsNormalizer
    import torch

    n = _ObsNormalizer(8)
    x = torch.tensor([[1.0, float("nan"), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    with torch.inference_mode():
        y = n(x)
    assert torch.isfinite(y).all()


# -------- RLPaperDrag._match_reference determinism --------

def test_match_reference_deterministic(rl_paper_drag):
    pose = np.array([0.30, 0.20, 0.1])
    a = rl_paper_drag._match_reference(pose)
    b = rl_paper_drag._match_reference(pose)
    assert a == b
    assert 0 <= a < len(rl_paper_drag.ref_lengths)


def test_match_reference_wrap_on_angle(rl_paper_drag):
    """Angle 3.14 and -3.14 should land on similar references (wrap symmetric)."""
    pose_a = np.array([0.25, 0.18, 3.14])
    pose_b = np.array([0.25, 0.18, -3.14])
    idx_a = rl_paper_drag._match_reference(pose_a)
    idx_b = rl_paper_drag._match_reference(pose_b)
    # Both should use wrap_angle-aware distance, so diff ≈ 0.0028, NOT ≈ 6.28.
    assert idx_a == idx_b


# -------- RLPaperDrag.sample_actions shape / range / determinism --------

def test_sample_actions_shape_and_range(rl_paper_drag):
    rl_paper_drag.reset(
        paper_pose=np.array([0.25, 0.18, 0.0]),
        joint_pos=np.zeros(6),
    )
    inputs = {
        "state": np.zeros(6),
        "paper_pose": np.array([0.25, 0.18, 0.0]),
        "dt": 0.05,
        "noise": False,
    }
    out = rl_paper_drag.sample_actions(inputs)
    assert out.shape == (1, 6)
    assert np.isfinite(out).all()
    # default_joint_pos=0 + raw_action∈[-1,1] * 0.5 → [-0.5, 0.5]
    assert np.all(out >= -0.5 - 1e-9)
    assert np.all(out <= 0.5 + 1e-9)


def test_sample_actions_deterministic_when_noise_off(rl_paper_drag):
    """With noise=False, the same inputs must yield the same action
    (history buffers advance identically because there is no RNG draw)."""
    from phosphobot.am.rl_paper_drag import RLPaperDrag
    # Fresh second instance via re-init (reset alone is not enough because
    # the MLP weights ARE deterministic but history state must match).
    # Instead, just verify that (reset then 1 step) is repeatable.
    rl_paper_drag.reset(np.array([0.25, 0.18, 0.0]), np.zeros(6))
    a = rl_paper_drag.sample_actions({
        "state": np.zeros(6),
        "paper_pose": np.array([0.25, 0.18, 0.0]),
        "dt": 0.05,
        "noise": False,
    })
    rl_paper_drag.reset(np.array([0.25, 0.18, 0.0]), np.zeros(6))
    b = rl_paper_drag.sample_actions({
        "state": np.zeros(6),
        "paper_pose": np.array([0.25, 0.18, 0.0]),
        "dt": 0.05,
        "noise": False,
    })
    np.testing.assert_allclose(a, b, atol=1e-9)


def test_sample_actions_noise_on_varies(rl_paper_drag):
    """With noise=True, same input produces different outputs across resets."""
    rl_paper_drag.reset(np.array([0.25, 0.18, 0.0]), np.zeros(6))
    np.random.seed(0)
    a = rl_paper_drag.sample_actions({
        "state": np.zeros(6),
        "paper_pose": np.array([0.25, 0.18, 0.0]),
        "dt": 0.05,
        "noise": True,
    })
    rl_paper_drag.reset(np.array([0.25, 0.18, 0.0]), np.zeros(6))
    np.random.seed(1)
    b = rl_paper_drag.sample_actions({
        "state": np.zeros(6),
        "paper_pose": np.array([0.25, 0.18, 0.0]),
        "dt": 0.05,
        "noise": True,
    })
    # Different seeds → different noise → different output
    assert not np.allclose(a, b, atol=1e-6)


# -------- fetch_and_verify_config error paths --------

@pytest.mark.parametrize("missing_name", [
    "best_run20_98pct.pt",
    "paper_yolo_obb.pt",
    "so101_nmpc_references.npz",
    "calibration.json",
])
def test_fetch_and_verify_config_missing_single_file(
    tmp_path, rl_assets_bundle, missing_name
):
    """Missing any one of the 4 required files → ValueError mentioning it."""
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    d = tmp_path / "partial"
    d.mkdir()
    for name in ("best_run20_98pct.pt", "paper_yolo_obb.pt",
                 "so101_nmpc_references.npz", "calibration.json"):
        if name == missing_name:
            continue
        (d / name).symlink_to((rl_assets_bundle / name).resolve())

    with pytest.raises(ValueError) as exc_info:
        RLPaperDrag.fetch_and_verify_config(
            model_id=str(d), all_cameras=None, robots=[object()],
        )
    assert missing_name in str(exc_info.value)


def test_fetch_and_verify_config_non_directory(tmp_path):
    from phosphobot.am.rl_paper_drag import RLPaperDrag
    nonexistent = tmp_path / "does_not_exist"
    with pytest.raises(ValueError) as exc_info:
        RLPaperDrag.fetch_and_verify_config(
            model_id=str(nonexistent), all_cameras=None, robots=[object()],
        )
    assert "directory" in str(exc_info.value).lower()


def test_fetch_and_verify_config_wrong_robot_count(rl_assets_bundle):
    from phosphobot.am.rl_paper_drag import RLPaperDrag
    with pytest.raises(ValueError) as exc_info:
        RLPaperDrag.fetch_and_verify_config(
            model_id=str(rl_assets_bundle),
            all_cameras=None,
            robots=[object(), object()],  # 2 robots — not allowed
        )
    assert "1 robot" in str(exc_info.value)


def test_fetch_and_verify_config_happy_path(rl_assets_bundle):
    from phosphobot.am.rl_paper_drag import RLPaperDrag, RLPaperDragSpawnConfig
    cfg = RLPaperDrag.fetch_and_verify_config(
        model_id=str(rl_assets_bundle),
        all_cameras=None,
        robots=[object()],
    )
    assert isinstance(cfg, RLPaperDragSpawnConfig)
    assert Path(cfg.checkpoint_path).exists()
    assert Path(cfg.yolo_model_path).exists()
    assert Path(cfg.reference_npz_path).exists()
    assert Path(cfg.calibration_json_path).exists()


# -------- fetch_and_get_configuration --------

def test_fetch_and_get_configuration_empty_video_keys():
    from phosphobot.am.rl_paper_drag import RLPaperDrag
    resp = RLPaperDrag.fetch_and_get_configuration("/some/path")
    assert resp.video_keys == []
    assert resp.checkpoints == []


# -------- Per-term buffer shape + first-step broadcast --------

def test_first_step_broadcasts_history(rl_paper_drag):
    """On first step, every row of each term buffer is the current obs
    (not just the last row)."""
    rl_paper_drag.reset(
        paper_pose=np.array([0.25, 0.18, 0.0]),
        joint_pos=np.zeros(6),
    )
    assert rl_paper_drag._is_first_step is True
    _ = rl_paper_drag.sample_actions({
        "state": np.zeros(6),
        "paper_pose": np.array([0.25, 0.18, 0.0]),
        "dt": 0.05,
        "noise": False,
    })
    assert rl_paper_drag._is_first_step is False
    # First step should have broadcast — all rows equal in each buffer
    for buf in rl_paper_drag._term_buffers:
        # All 50 rows should be identical after broadcast
        assert np.allclose(buf, buf[0:1, :])


def test_term_buffer_shapes(rl_paper_drag):
    expected_dims = (6, 6, 3, 3, 3, 6, 6)
    assert len(rl_paper_drag._term_buffers) == len(expected_dims)
    for buf, d in zip(rl_paper_drag._term_buffers, expected_dims):
        assert buf.shape == (50, d)


# -------- Angle-format unit mapping (static dict) --------

def test_angle_format_unit_mapping():
    """The unit-mapping dict inside control_loop must map radians→rad,
    degrees→degrees, other→other. Test by inspecting the string source —
    a broken dict silently corrupts servo commands (see gap #3 in plan v2)."""
    import inspect
    from phosphobot.am.rl_paper_drag import RLPaperDrag
    src = inspect.getsource(RLPaperDrag.control_loop)
    # The dict literal must be present and correct
    assert '"radians": "rad"' in src
    assert '"degrees": "degrees"' in src
    assert '"other": "other"' in src
