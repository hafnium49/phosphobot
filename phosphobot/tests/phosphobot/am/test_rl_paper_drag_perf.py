"""Performance / timing tests for RLPaperDrag (soft asserts).

These tests WARN but do not fail on slow results, because WSL2 timing is
not predictive of Pi 4 performance. They exist to catch egregious regressions
(e.g. someone accidentally calls .train() or loads weights per step).

Hard fail only on CORRECTNESS invariants (finiteness, shape).
"""
from __future__ import annotations

import time
import warnings

import numpy as np
import pytest


def test_mlp_forward_timing_budget(rl_paper_drag):
    """MLP forward pass alone should comfortably fit in 20 Hz budget."""
    import torch
    rl_paper_drag.reset(np.array([0.25, 0.18, 0.0]), np.zeros(6))

    obs = torch.zeros(1, 1650)
    # Warmup
    with torch.inference_mode():
        for _ in range(3):
            _ = rl_paper_drag.actor(rl_paper_drag.obs_normalizer(obs))

    n = 50
    t0 = time.perf_counter()
    with torch.inference_mode():
        for _ in range(n):
            _ = rl_paper_drag.actor(rl_paper_drag.obs_normalizer(obs))
    elapsed_ms = (time.perf_counter() - t0) / n * 1000

    # Soft: warn if > 10ms (still fits 20 Hz = 50ms budget with slack)
    if elapsed_ms > 10.0:
        warnings.warn(
            f"MLP forward > 10ms ({elapsed_ms:.2f}ms). Investigate if on Pi 4."
        )
    # Hard: must fit 20 Hz budget in ANY sane environment
    assert elapsed_ms < 50.0, f"MLP forward too slow: {elapsed_ms:.2f}ms > 50ms"


def test_full_sample_actions_budget(rl_paper_drag):
    """Full sample_actions (obs build + normalize + forward + scale) budget."""
    rl_paper_drag.reset(np.array([0.25, 0.18, 0.0]), np.zeros(6))

    inputs = {
        "state": np.zeros(6),
        "paper_pose": np.array([0.25, 0.18, 0.0]),
        "dt": 0.05,
        "noise": False,
    }
    # Warmup
    for _ in range(3):
        _ = rl_paper_drag.sample_actions(inputs)

    n = 30
    t0 = time.perf_counter()
    for _ in range(n):
        _ = rl_paper_drag.sample_actions(inputs)
    elapsed_ms = (time.perf_counter() - t0) / n * 1000

    if elapsed_ms > 15.0:
        warnings.warn(
            f"sample_actions > 15ms ({elapsed_ms:.2f}ms). Excluding YOLO, "
            f"total Pi 4 budget leaves ~25ms for vision. Investigate if slow."
        )
    # Hard cap: must fit 20 Hz on the slowest plausible host
    assert elapsed_ms < 50.0, f"sample_actions too slow: {elapsed_ms:.2f}ms"


def test_match_reference_fast(rl_paper_drag):
    """Reference matching is O(N) linalg — should be sub-ms on 19k refs."""
    pose = np.array([0.25, 0.18, 0.0])
    # Warmup
    for _ in range(3):
        _ = rl_paper_drag._match_reference(pose)

    n = 100
    t0 = time.perf_counter()
    for _ in range(n):
        _ = rl_paper_drag._match_reference(pose)
    elapsed_ms = (time.perf_counter() - t0) / n * 1000

    assert elapsed_ms < 5.0, f"_match_reference too slow: {elapsed_ms:.2f}ms"
