"""Security tests for RLPaperDrag: which weight files it unpickles, and where it publishes.

Nothing here needs the real assets: every checkpoint is a small fake built in
tmp_path, the YOLO detector is a stub and the ZMQ context is a fake, so no file
outside tmp_path is read and no socket is opened.

Covers:
    - the checkpoint is loaded only if it resolves inside the models root
      (PHOSPHOBOT_RL_PAPER_DRAG_MODELS_ROOT), also through symlinks and ".."
    - the checkpoint is loaded with weights_only=True; a pickle that carries
      a call is refused and the call does not run
    - the YOLO weights (a full pickle, loaded by ultralytics) obey the same root
      and are loaded from the resolved path that was checked
    - fetch_and_verify_config refuses such a model_id before anything is loaded
    - the detection publisher binds to 127.0.0.1 unless
      PHOSPHOBOT_RL_PAPER_DRAG_PUB_HOST names another interface
"""
from __future__ import annotations

import os
import pickle
import shutil
from pathlib import Path

import numpy as np
import pytest

ROOT_ENV = "PHOSPHOBOT_RL_PAPER_DRAG_MODELS_ROOT"
PUB_HOST_ENV = "PHOSPHOBOT_RL_PAPER_DRAG_PUB_HOST"
CKPT = "best_run20_98pct.pt"
YOLO = "paper_yolo_obb.pt"
NPZ = "so101_nmpc_references.npz"
CAL = "calibration.json"
PUB_PORT = 45555  # never bound: the ZMQ context is a fake


def _actor_state_dict():
    """A state dict with the keys and shapes of the Run #20 checkpoint."""
    import torch
    from phosphobot.am.rl_paper_drag import _ActorMLP, _ObsNormalizer

    torch.manual_seed(0)
    sd = dict(_ActorMLP(1650, 6, [512, 256, 128]).state_dict())
    sd.update(
        {f"obs_normalizer.{k}": v for k, v in _ObsNormalizer(1650).state_dict().items()}
    )
    return sd


class _Call:
    """Unpickling this object calls os.mkdir(marker): a stand-in for any code."""

    def __init__(self, marker: Path):
        self.marker = marker

    def __reduce__(self):
        return (os.mkdir, (str(self.marker),))


class _StubYOLO:
    """Stands in for YOLOVisionSystem; records what it was built with."""

    built: list = []

    def __init__(self, **kwargs):
        _StubYOLO.built.append(kwargs)


class _LoadSpy:
    """Wraps torch.load and records every call."""

    def __init__(self, real):
        self.real = real
        self.calls: list = []

    def __call__(self, f, *args, **kwargs):
        self.calls.append((str(f), kwargs))
        return self.real(f, *args, **kwargs)


class _Rig:
    """The layout start_phosphobot_rl.sh builds, in tmp_path.

    root/    the models root: the checkpoint and the YOLO weights
    repo/    the reference trajectories and the calibration
    bundle/  four symlinks to them; this is the model_id of a request
    outside/ a directory that is not under the models root
    """

    def __init__(self, tmp_path: Path):
        import torch

        self.root = tmp_path / "models"
        self.repo = tmp_path / "repo"
        self.bundle = tmp_path / "bundle"
        self.outside = tmp_path / "outside"
        for d in (self.root, self.repo, self.bundle, self.outside):
            d.mkdir()
        self.state_dict = _actor_state_dict()
        torch.save({"actor_state_dict": self.state_dict, "iter": 7}, self.root / CKPT)
        (self.root / YOLO).write_bytes(b"stub weights")
        np.savez(
            self.repo / NPZ,
            paper_trajectories=np.zeros((2, 3, 3)),
            joint_trajectories=np.zeros((2, 3, 6)),
            episode_lengths=np.array([3, 3]),
            initial_poses=np.zeros((2, 3)),
        )
        (self.repo / CAL).write_text("{}")
        (self.bundle / CKPT).symlink_to(self.root / CKPT)
        (self.bundle / YOLO).symlink_to(self.root / YOLO)
        (self.bundle / NPZ).symlink_to(self.repo / NPZ)
        (self.bundle / CAL).symlink_to(self.repo / CAL)

    def cfg(self, **overrides):
        from phosphobot.am.rl_paper_drag import RLPaperDragSpawnConfig

        fields = dict(
            model_dir=str(self.bundle),
            checkpoint_path=str(self.bundle / CKPT),
            yolo_model_path=str(self.bundle / YOLO),
            reference_npz_path=str(self.bundle / NPZ),
            calibration_json_path=str(self.bundle / CAL),
            publish_detections_port=None,
            device="cpu",
        )
        fields.update(overrides)
        return RLPaperDragSpawnConfig(**fields)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    import phosphobot.am.rl_paper_drag as mod

    rig = _Rig(tmp_path)
    monkeypatch.setenv(ROOT_ENV, str(rig.root))
    monkeypatch.delenv(PUB_HOST_ENV, raising=False)
    _StubYOLO.built = []
    monkeypatch.setattr(mod, "YOLOVisionSystem", _StubYOLO)
    return rig


@pytest.fixture
def load_spy(monkeypatch):
    import torch

    spy = _LoadSpy(torch.load)
    monkeypatch.setattr(torch, "load", spy)
    return spy


# -------- the checkpoint: where it may come from --------

def test_bundle_of_symlinks_into_the_root_is_loaded(rig, load_spy):
    """The deployed layout: model_id is outside the root, its files point into it."""
    import torch
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    m = RLPaperDrag(rig.cfg())

    assert torch.equal(m.actor.mlp[0].weight, rig.state_dict["mlp.0.weight"])
    assert len(load_spy.calls) == 1


def test_the_file_that_is_loaded_is_the_resolved_one(rig, load_spy):
    """What was checked is what is read: not the symlink, which could change."""
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    RLPaperDrag(rig.cfg())

    assert load_spy.calls[0][0] == str((rig.root / CKPT).resolve())


def test_dotdot_that_stays_inside_the_root_is_loaded(rig, load_spy):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    (rig.root / "sub").mkdir()
    RLPaperDrag(rig.cfg(checkpoint_path=str(rig.root / "sub" / ".." / CKPT)))

    assert len(load_spy.calls) == 1


def test_checkpoint_outside_the_root_is_refused_and_not_loaded(rig, load_spy):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    shutil.copy(rig.root / CKPT, rig.outside / CKPT)

    with pytest.raises(ValueError, match="outside the models root"):
        RLPaperDrag(rig.cfg(checkpoint_path=str(rig.outside / CKPT)))
    assert load_spy.calls == []


def test_symlink_inside_the_root_that_leaves_it_is_refused(rig, load_spy):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    shutil.copy(rig.root / CKPT, rig.outside / CKPT)
    (rig.root / "escape.pt").symlink_to(rig.outside / CKPT)

    with pytest.raises(ValueError, match="outside the models root"):
        RLPaperDrag(rig.cfg(checkpoint_path=str(rig.root / "escape.pt")))
    assert load_spy.calls == []


def test_symlinked_directory_inside_the_root_that_leaves_it_is_refused(rig, load_spy):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    shutil.copy(rig.root / CKPT, rig.outside / CKPT)
    (rig.root / "linked").symlink_to(rig.outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside the models root"):
        RLPaperDrag(rig.cfg(checkpoint_path=str(rig.root / "linked" / CKPT)))
    assert load_spy.calls == []


def test_dotdot_out_of_the_root_is_refused(rig, load_spy):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    shutil.copy(rig.root / CKPT, rig.outside / CKPT)

    with pytest.raises(ValueError, match="outside the models root"):
        RLPaperDrag(
            rig.cfg(checkpoint_path=str(rig.root / ".." / "outside" / CKPT))
        )
    assert load_spy.calls == []


def test_directory_whose_name_starts_like_the_root_is_outside(rig, load_spy, tmp_path):
    """/x/models-evil is not inside /x/models."""
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    sibling = tmp_path / "models-evil"
    sibling.mkdir()
    shutil.copy(rig.root / CKPT, sibling / CKPT)

    with pytest.raises(ValueError, match="outside the models root"):
        RLPaperDrag(rig.cfg(checkpoint_path=str(sibling / CKPT)))
    assert load_spy.calls == []


def test_empty_root_variable_means_the_default_root_not_the_working_directory(
    rig, load_spy, monkeypatch, tmp_path
):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    monkeypatch.setenv(ROOT_ENV, "")
    monkeypatch.chdir(tmp_path)  # the checkpoint is under the working directory

    with pytest.raises(ValueError, match="outside the models root"):
        RLPaperDrag(rig.cfg())
    assert load_spy.calls == []


# -------- the checkpoint: how it is unpickled --------

def test_checkpoint_is_loaded_with_weights_only(rig, load_spy):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    RLPaperDrag(rig.cfg())

    assert load_spy.calls[0][1].get("weights_only") is True


def test_pickle_that_carries_a_call_is_refused_and_the_call_does_not_run(
    rig, tmp_path
):
    """A file inside the root is still not trusted to run code."""
    import torch
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    marker = tmp_path / "the_call_ran"
    torch.save(
        {"actor_state_dict": rig.state_dict, "iter": 7, "infos": _Call(marker)},
        rig.root / CKPT,
    )

    with pytest.raises(pickle.UnpicklingError):
        RLPaperDrag(rig.cfg())
    assert not marker.exists()


# -------- the YOLO weights: a full pickle, so the same root --------

def test_yolo_weights_outside_the_root_are_refused_and_not_loaded(rig):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    (rig.outside / YOLO).write_bytes(b"stub weights")

    with pytest.raises(ValueError, match="outside the models root"):
        RLPaperDrag(rig.cfg(yolo_model_path=str(rig.outside / YOLO)))
    assert _StubYOLO.built == []


def test_yolo_symlink_inside_the_root_that_leaves_it_is_refused(rig):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    (rig.outside / YOLO).write_bytes(b"stub weights")
    (rig.root / "escape_obb.pt").symlink_to(rig.outside / YOLO)

    with pytest.raises(ValueError, match="outside the models root"):
        RLPaperDrag(rig.cfg(yolo_model_path=str(rig.root / "escape_obb.pt")))
    assert _StubYOLO.built == []


def test_yolo_loader_gets_the_resolved_path_not_the_symlink(rig):
    """What was checked is what is read; the name as given only tells the kind."""
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    RLPaperDrag(rig.cfg())

    assert _StubYOLO.built[0]["model_path"] == str((rig.root / YOLO).resolve())
    assert _StubYOLO.built[0]["model_name"] == str(rig.bundle / YOLO)


class _StubUltralyticsYOLO:
    """Stands in for ultralytics.YOLO; records the path it was asked to load."""

    loaded: list = []
    task = "detect"

    def __init__(self, path):
        _StubUltralyticsYOLO.loaded.append(path)


@pytest.fixture
def stub_ultralytics(monkeypatch):
    import ultralytics

    _StubUltralyticsYOLO.loaded = []
    monkeypatch.setattr(ultralytics, "YOLO", _StubUltralyticsYOLO)
    return _StubUltralyticsYOLO


def test_yolo_vision_system_loads_model_path_and_reads_the_kind_from_model_name(
    tmp_path, stub_ultralytics
):
    from phosphobot.am.yolo_vision_adapter import YOLOVisionSystem

    real = tmp_path / "weights.pt"
    real.write_bytes(b"stub weights")

    v = YOLOVisionSystem(model_path=str(real), model_name="bundle/paper_yolo_obb_v2.pt")

    assert stub_ultralytics.loaded == [str(real)]
    assert (v.is_obb_model, v.is_v2_model, v.is_pose_model) == (True, True, False)


def test_yolo_vision_system_without_model_name_reads_the_kind_from_model_path(
    tmp_path, stub_ultralytics
):
    """As before, for every other caller."""
    from phosphobot.am.yolo_vision_adapter import YOLOVisionSystem

    real = tmp_path / "paper_yolo_pose.pt"
    real.write_bytes(b"stub weights")

    v = YOLOVisionSystem(model_path=str(real))

    assert stub_ultralytics.loaded == [str(real)]
    assert (v.is_obb_model, v.is_v2_model, v.is_pose_model) == (False, False, True)


# -------- fetch_and_verify_config: the request is refused before any load --------

def test_fetch_and_verify_config_accepts_the_bundle(rig):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    cfg = RLPaperDrag.fetch_and_verify_config(
        model_id=str(rig.bundle), all_cameras=None, robots=[object()]
    )

    assert cfg.checkpoint_path == str(rig.bundle / CKPT)


def test_fetch_and_verify_config_accepts_a_relative_model_id(rig, monkeypatch, tmp_path):
    """A relative model_id is relative to the working directory, as before."""
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    monkeypatch.chdir(tmp_path)
    cfg = RLPaperDrag.fetch_and_verify_config(
        model_id="bundle", all_cameras=None, robots=[object()]
    )

    RLPaperDrag(cfg.model_copy(update={"publish_detections_port": None}))


@pytest.mark.parametrize("name", [CKPT, YOLO])
def test_fetch_and_verify_config_refuses_weights_outside_the_root(rig, name):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    (rig.bundle / name).unlink()
    shutil.copy(rig.root / name, rig.bundle / name)  # a file of the caller's own

    with pytest.raises(ValueError, match="outside the models root") as exc_info:
        RLPaperDrag.fetch_and_verify_config(
            model_id=str(rig.bundle), all_cameras=None, robots=[object()]
        )
    assert name in str(exc_info.value)
    assert ROOT_ENV in str(exc_info.value)


# -------- the detection publisher: which interface --------

class _FakeSocket:
    def __init__(self):
        self.bound: list = []

    def bind(self, endpoint):
        self.bound.append(endpoint)


class _FakeContext:
    def __init__(self):
        self.sock = _FakeSocket()

    def socket(self, kind):
        return self.sock


@pytest.fixture
def fake_zmq(monkeypatch):
    import zmq

    ctx = _FakeContext()
    monkeypatch.setattr(zmq, "Context", lambda: ctx)
    return ctx.sock


def test_publisher_binds_to_loopback_by_default(rig, fake_zmq):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    RLPaperDrag(rig.cfg(publish_detections_port=PUB_PORT))

    assert fake_zmq.bound == [f"tcp://127.0.0.1:{PUB_PORT}"]


@pytest.mark.parametrize("host", ["192.168.1.50", "*"])
def test_publisher_binds_to_the_interface_the_variable_names(
    rig, fake_zmq, monkeypatch, host
):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    monkeypatch.setenv(PUB_HOST_ENV, host)
    RLPaperDrag(rig.cfg(publish_detections_port=PUB_PORT))

    assert fake_zmq.bound == [f"tcp://{host}:{PUB_PORT}"]


def test_empty_publisher_variable_means_loopback(rig, fake_zmq, monkeypatch):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    monkeypatch.setenv(PUB_HOST_ENV, "")
    RLPaperDrag(rig.cfg(publish_detections_port=PUB_PORT))

    assert fake_zmq.bound == [f"tcp://127.0.0.1:{PUB_PORT}"]


def test_no_port_no_publisher(rig, fake_zmq):
    from phosphobot.am.rl_paper_drag import RLPaperDrag

    RLPaperDrag(rig.cfg(publish_detections_port=None))

    assert fake_zmq.bound == []
