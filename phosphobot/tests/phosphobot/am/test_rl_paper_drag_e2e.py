"""End-to-end / dispatch wiring tests for RLPaperDrag.

These tests guard against the most common "silent" integration bugs:
    - setup_ai_control's model_types dict wiring
    - StartAIControlRequest Pydantic Literal accepts "rl_paper_drag"
    - ModelConfigurationRequest Pydantic Literal accepts "rl_paper_drag"
    - phosphobot.am exports RLPaperDrag + RLPaperDragSpawnConfig
    - RLPaperDrag satisfies the ActionModel ABC contract
"""
from __future__ import annotations

import inspect

import pytest


def test_rl_paper_drag_exported_from_phosphobot_am():
    from phosphobot.am import RLPaperDrag, RLPaperDragSpawnConfig
    assert RLPaperDrag is not None
    assert RLPaperDragSpawnConfig is not None


def test_dispatch_wiring_in_setup_ai_control():
    """setup_ai_control's model_types dict MUST contain "rl_paper_drag"
    → RLPaperDrag. Prevents the classic enum-added-but-dispatch-forgotten bug."""
    src = inspect.getsource(
        __import__("phosphobot.ai_control", fromlist=["setup_ai_control"]).setup_ai_control
    )
    assert '"rl_paper_drag": RLPaperDrag' in src


def test_start_ai_control_request_literal_accepts_rl_paper_drag():
    """Pydantic must accept model_type='rl_paper_drag' (Literal enum)."""
    from phosphobot.models import StartAIControlRequest
    req = StartAIControlRequest(
        model_id="/some/local/dir",
        model_type="rl_paper_drag",
    )
    assert req.model_type == "rl_paper_drag"


def test_start_ai_control_request_rejects_typo():
    """Typo should fail validation (defensive: protects against enum drift)."""
    from pydantic import ValidationError
    from phosphobot.models import StartAIControlRequest
    with pytest.raises(ValidationError):
        StartAIControlRequest(
            model_id="/some/local/dir",
            model_type="rl_paperdrag",  # missing underscore
        )


def test_model_configuration_request_accepts_rl_paper_drag():
    from phosphobot.models import ModelConfigurationRequest
    req = ModelConfigurationRequest(
        model_id="/some/local/dir",
        model_type="rl_paper_drag",
    )
    assert req.model_type == "rl_paper_drag"


def test_rl_paper_drag_satisfies_action_model_abc():
    """RLPaperDrag must implement all required ActionModel abstract methods."""
    from phosphobot.am.base import ActionModel
    from phosphobot.am.rl_paper_drag import RLPaperDrag
    assert issubclass(RLPaperDrag, ActionModel)
    # Required abstract methods (see phosphobot/am/base.py)
    for method in ("sample_actions", "control_loop", "fetch_and_verify_config"):
        assert hasattr(RLPaperDrag, method)
        assert callable(getattr(RLPaperDrag, method))


def test_control_loop_signature_matches_ai_control_call_pattern():
    """ai_control.py calls control_loop with specific kwargs; verify signature
    accepts all of them (or absorbs via **kwargs)."""
    from phosphobot.am.rl_paper_drag import RLPaperDrag
    sig = inspect.signature(RLPaperDrag.control_loop)
    params = sig.parameters
    for required in ("control_signal", "robots", "model_spawn_config",
                     "all_cameras", "prompt", "fps", "speed",
                     "cameras_keys_mapping", "angle_format"):
        assert required in params, f"control_loop missing kwarg: {required}"
    # Must accept **kwargs for forward compat (ai_control may pass extras)
    assert any(p.kind == p.VAR_KEYWORD for p in params.values()), \
        "control_loop must accept **kwargs"
