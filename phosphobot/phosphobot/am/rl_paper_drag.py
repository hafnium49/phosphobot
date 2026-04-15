"""RLPaperDrag: Run #20 paper-dragging RL policy as a phosphobot ActionModel.

Runs the Run #20 trained MLP policy (98% mjlab eval) as a native phosphobot
AI control model, using the same in-process patterns as gr00t/ACT/pi0.5/smolvla.

Architecture (all in-process on the robot's host — no HTTP in the hot path):
  - Load MLP actor weights from local .pt checkpoint.
  - Load NMPC reference trajectories from local .npz.
  - Load YOLO-OBB paper detector (YOLOVisionSystem) from local .pt.
  - Each control step:
      * Read joints from robots[0] via motors_bus      (~0.5ms)
      * Read latest camera frame via all_cameras       (~1ms, cached thread)
      * Run YOLO-OBB → paper_pose (x, y, theta)        (~25ms CPU on x86, ~60-90ms on Pi 4)
      * Build 1650D term-major observation
      * Forward pass through actor MLP                 (~5ms CPU)
      * Write 6D joint target via motors_bus           (~0.5ms)
  - Optional: publish detected paper_pose on ZMQ PUB for external overlay.

Observation space: 33 dims/step × 50 step history = 1650 flat, term-major order:
  joint_pos_rel(6), joint_vel_rel(6), paper_pose(3), target_error(3),
  ref_tracking_error(3), joint_ref_error(6), last_action(6)

Action space: 6 joint position deltas, clipped to [-1, 1], scaled by 0.5,
added to default_joint_pos=zeros(6). Commanded in radians to Feetech STS3215.

Ported from /home/hafnium/so101-rl-deploy/rl_policy_controller.py (RLPolicyController).
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, List, Literal, Optional

import numpy as np
import torch
import torch.nn as nn
import zmq
from loguru import logger
from pydantic import BaseModel, Field

from phosphobot.am.base import ActionModel
from phosphobot.am.yolo_vision_adapter import YOLOVisionSystem
from phosphobot.camera import AllCameras
from phosphobot.control_signal import AIControlSignal
from phosphobot.hardware.base import BaseManipulator
from phosphobot.models import ModelConfigurationResponse


# --- MLP / Normalizer (ported verbatim from rl_policy_controller.py:23-55) ---

class _ActorMLP(nn.Module):
    """Standalone actor MLP matching rsl_rl's ActorCritic architecture."""

    def __init__(self, obs_dim: int, act_dim: int, hidden_dims: List[int]):
        super().__init__()
        layers = []
        in_dim = obs_dim
        for h in hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.ELU())
            in_dim = h
        layers.append(nn.Linear(in_dim, act_dim))
        self.mlp = nn.Sequential(*layers)
        self.std = nn.Parameter(torch.zeros(act_dim))

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.mlp(obs)


class _ObsNormalizer(nn.Module):
    """Standalone observation normalizer matching rsl_rl's EmpiricalNormalization."""

    def __init__(self, obs_dim: int, eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.register_buffer("_mean", torch.zeros(1, obs_dim))
        self.register_buffer("_var", torch.ones(1, obs_dim))
        self.register_buffer("_std", torch.ones(1, obs_dim))
        self.register_buffer("count", torch.tensor(0, dtype=torch.long))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.nan_to_num(x, nan=0.0)
        return (x - self._mean) / (self._std + self.eps)


def _wrap_angle(angle: float) -> float:
    """Wrap angle to [-π, π]."""
    return float(np.arctan2(np.sin(angle), np.cos(angle)))


# --- Spawn config (returned by fetch_and_verify_config) ---

class RLPaperDragSpawnConfig(BaseModel):
    """Configuration for RLPaperDrag, produced by fetch_and_verify_config.

    Unlike gr00t/lerobot models, we don't use HuggingFace — weights are local.
    model_id is interpreted as a directory containing the 4 required files.
    """
    model_dir: str = Field(..., description="Local directory with policy + assets")
    checkpoint_path: str = Field(..., description="Path to best_run20_98pct.pt (RL policy)")
    yolo_model_path: str = Field(..., description="Path to paper_yolo_obb.pt (vision)")
    reference_npz_path: str = Field(..., description="Path to so101_nmpc_references.npz")
    calibration_json_path: str = Field(..., description="Path to calibration.json")
    camera_id: int = Field(default=0, description="Camera id (0 = top view by default)")
    publish_detections_port: Optional[int] = Field(
        default=5555,
        description="ZMQ PUB port for paper_pose detections (for external overlay). None to disable.",
    )
    device: Literal["cpu", "cuda"] = "cpu"


# --- The ActionModel class ---

class RLPaperDrag(ActionModel):
    """Run #20 paper-dragging RL policy as a phosphobot native ActionModel.

    See module docstring for architecture. Subscribe to control via
    POST /ai-control/start with model_type="rl_paper_drag" and
    model_id set to a local directory containing the 4 required assets.
    """

    OBS_DIM_PER_STEP = 33
    HISTORY_LENGTH = 50
    NUM_JOINTS = 6
    ACTION_SCALE = 0.5
    # Per-term dimensions matching training observation order
    TERM_DIMS = (6, 6, 3, 3, 3, 6, 6)
    # Observation noise matching training (paper_drag_env_cfg.py)
    OBS_NOISE_JOINT_POS = 0.01   # ±0.01 rad uniform
    OBS_NOISE_JOINT_VEL = 1.5    # ±1.5 rad/s uniform
    OBS_NOISE_PAPER_POS = 0.005  # ±5mm uniform on x,y

    def __init__(self, cfg: RLPaperDragSpawnConfig):
        super().__init__()
        self.cfg = cfg
        self.device = torch.device(cfg.device)

        # ---- Load NMPC reference trajectories ----
        data = np.load(cfg.reference_npz_path)
        self.ref_paper = data["paper_trajectories"]     # (N, T, 3)
        self.ref_joints = data["joint_trajectories"]    # (N, T, 6)
        self.ref_lengths = data["episode_lengths"]      # (N,)
        self.ref_initial_poses = data["initial_poses"]  # (N, 3)
        logger.info(f"[RLPaperDrag] Loaded {len(self.ref_lengths)} reference trajectories")

        # ---- Load target pose from calibration ----
        cal = json.loads(Path(cfg.calibration_json_path).read_text())
        yv = cal.get("yolo_vision", {})
        ws = cal.get("workspace", {})
        fc = ws.get("frame_center", [0.275, 0.175])
        self.target_pose = np.array([fc[0], fc[1], np.pi / 2])
        logger.info(f"[RLPaperDrag] target_pose = {self.target_pose}")

        # ---- Build actor network ----
        obs_dim = self.OBS_DIM_PER_STEP * self.HISTORY_LENGTH  # 1650
        act_dim = self.NUM_JOINTS
        self.actor = _ActorMLP(obs_dim, act_dim, hidden_dims=[512, 256, 128])
        self.obs_normalizer = _ObsNormalizer(obs_dim)

        # ---- Load checkpoint ----
        ckpt = torch.load(cfg.checkpoint_path, map_location=self.device, weights_only=False)
        actor_sd = ckpt["actor_state_dict"]

        norm_sd = {k.replace("obs_normalizer.", ""): v for k, v in actor_sd.items()
                   if k.startswith("obs_normalizer.")}
        mlp_sd = {k: v for k, v in actor_sd.items()
                  if k.startswith("mlp.") or k == "std"}
        self.obs_normalizer.load_state_dict(norm_sd, strict=True)
        self.actor.load_state_dict(mlp_sd, strict=True)

        self.actor.to(self.device).eval()
        self.obs_normalizer.to(self.device).eval()
        logger.info(f"[RLPaperDrag] Loaded checkpoint {cfg.checkpoint_path} "
                    f"(iter {ckpt.get('iter', '?')})")

        # ---- In-process YOLO detector (constructor takes individual calib params,
        #      NOT a path — see yolo_vision_adapter.py:43-56) ----
        self.yolo = YOLOVisionSystem(
            model_path=cfg.yolo_model_path,
            conf_threshold=0.05,
            pixels_per_meter=float(yv.get("pixels_per_meter_x", 1043.0)),
            pixels_per_meter_y=(float(yv["pixels_per_meter_y"])
                                if "pixels_per_meter_y" in yv else None),
            camera_center_world=tuple(yv.get("camera_center_world", (0.275, 0.175))),
            pixel_axes=yv.get("pixel_axes"),
            angle_offset_deg=float(yv.get("angle_offset_deg", 0.0)),
            camera_rotation="real",
            input_bgr=True,
            device="cpu",
        )
        self._last_paper_pose: Optional[np.ndarray] = None

        # ---- Default joint positions (home pose = all zeros for SO-101) ----
        self.default_joint_pos = np.zeros(self.NUM_JOINTS)

        # ---- Per-episode state ----
        self._term_buffers = [np.zeros((self.HISTORY_LENGTH, d)) for d in self.TERM_DIMS]
        self._is_first_step = True
        self._last_action = np.zeros(self.NUM_JOINTS)
        self._prev_joint_pos: Optional[np.ndarray] = None
        self._step_count = 0
        self._ref_idx = 0
        self._ref_start_step = 0
        self._ref_length = 0

        # ---- Optional ZMQ PUB for external live overlay ----
        self._zmq_ctx: Optional[zmq.Context] = None
        self._detection_pub = None
        if cfg.publish_detections_port is not None:
            self._zmq_ctx = zmq.Context()
            self._detection_pub = self._zmq_ctx.socket(zmq.PUB)
            self._detection_pub.bind(f"tcp://*:{cfg.publish_detections_port}")
            logger.info(f"[RLPaperDrag] Publishing detections on "
                        f"tcp://*:{cfg.publish_detections_port}")

    # -------------------- Reference matching / reset --------------------

    def _match_reference(self, paper_pose: np.ndarray) -> int:
        """Match paper pose to nearest reference trajectory.

        Uses same metric as training: total_dist = pos_dist + 0.3 * angle_dist.
        Deterministic top-1 selection (matches rl_policy_controller.py:339).
        """
        pos_dist = np.linalg.norm(paper_pose[:2] - self.ref_initial_poses[:, :2], axis=1)
        angle_diff = paper_pose[2] - self.ref_initial_poses[:, 2]
        angle_dist = np.abs(np.arctan2(np.sin(angle_diff), np.cos(angle_diff)))
        total_dist = pos_dist + 0.3 * angle_dist
        return int(np.argmin(total_dist))

    def reset(self, paper_pose: np.ndarray, joint_pos: np.ndarray):
        """Reset for a new episode: match reference, clear history, reset counters."""
        self._ref_idx = self._match_reference(paper_pose)
        self._ref_start_step = 0
        self._ref_length = int(self.ref_lengths[self._ref_idx])
        for buf in self._term_buffers:
            buf[:] = 0.0
        self._is_first_step = True
        self._last_action[:] = 0.0
        self._prev_joint_pos = joint_pos.copy()
        self._step_count = 0
        logger.info(f"[RLPaperDrag] Reset: ref #{self._ref_idx} (len={self._ref_length}) "
                    f"paper=({paper_pose[0]*100:.1f},{paper_pose[1]*100:.1f})cm "
                    f"θ={np.degrees(paper_pose[2]):.1f}°")

    # -------------------- Vision (in-process YOLO) --------------------

    def _detect_paper_pose(self, frame_bgr: np.ndarray) -> Optional[np.ndarray]:
        """YOLO-OBB → paper_pose (x, y, θ) in world frame.

        YOLOVisionSystem.detect_paper_pose (yolo_vision_adapter.py:258) returns
        Optional[np.ndarray([x, y, theta])]. If this frame has no detection,
        return the cached last pose so the policy still gets a valid input.
        """
        pose = self.yolo.detect_paper_pose(frame_bgr)
        if pose is not None:
            self._last_paper_pose = pose
            if self._detection_pub is not None:
                try:
                    self._detection_pub.send_json({
                        "x": float(pose[0]),
                        "y": float(pose[1]),
                        "theta": float(pose[2]),
                        "timestamp": time.time(),
                    }, flags=zmq.NOBLOCK)
                except zmq.Again:
                    pass
        return self._last_paper_pose

    # -------------------- Observation + action --------------------

    def _build_observation_and_act(self, joint_pos: np.ndarray, paper_pose: np.ndarray,
                                   dt: float) -> np.ndarray:
        """Ported from RLPolicyController.compute_action (rl_policy_controller.py:192-317)."""
        # 1. Relative joint pos/vel (finite diff for velocity)
        joint_pos_rel = joint_pos - self.default_joint_pos
        if self._prev_joint_pos is not None:
            joint_vel = (joint_pos - self._prev_joint_pos) / max(dt, 1e-6)
        else:
            joint_vel = np.zeros(self.NUM_JOINTS)
        self._prev_joint_pos = joint_pos.copy()

        # 2. Reference slice (clamped at trajectory end)
        ref_t = min(self._step_count + self._ref_start_step, self._ref_length - 1)
        ref_paper = self.ref_paper[self._ref_idx, ref_t].copy()
        ref_joints = self.ref_joints[self._ref_idx, ref_t].copy()

        # 3. Observation features
        target_err = self.target_pose - paper_pose
        target_err[2] = _wrap_angle(target_err[2])
        ref_err = ref_paper - paper_pose
        ref_err[2] = _wrap_angle(ref_err[2])
        joint_ref_err = ref_joints - joint_pos

        # 3b. Observation noise matching training (deployment runs with noise=False,
        # but kept here so the code path matches compute_action exactly if needed).
        # Disabled by default; to re-enable, toggle the if-guard.
        add_noise = False
        if add_noise:
            joint_pos_rel = joint_pos_rel + np.random.uniform(
                -self.OBS_NOISE_JOINT_POS, self.OBS_NOISE_JOINT_POS, self.NUM_JOINTS)
            joint_vel = joint_vel + np.random.uniform(
                -self.OBS_NOISE_JOINT_VEL, self.OBS_NOISE_JOINT_VEL, self.NUM_JOINTS)
            paper_pose_obs = paper_pose.copy()
            paper_pose_obs[:2] += np.random.uniform(
                -self.OBS_NOISE_PAPER_POS, self.OBS_NOISE_PAPER_POS, 2)
        else:
            paper_pose_obs = paper_pose

        # 4. Assemble per-term observation parts (training order)
        obs_parts = [
            joint_pos_rel,        # 6
            joint_vel,            # 6
            paper_pose_obs,       # 3
            target_err,           # 3
            ref_err,              # 3
            joint_ref_err,        # 6
            self._last_action,    # 6
        ]

        # 5. History buffer update (first step broadcasts, then roll)
        if self._is_first_step:
            for i, part in enumerate(obs_parts):
                self._term_buffers[i][:] = part
            self._is_first_step = False
        else:
            for i, part in enumerate(obs_parts):
                self._term_buffers[i] = np.roll(self._term_buffers[i], -1, axis=0)
                self._term_buffers[i][-1] = part

        # 6. TERM-MAJOR flatten → 1650D vector
        obs_flat = np.concatenate([buf.flatten() for buf in self._term_buffers])

        # 7. Forward pass
        with torch.inference_mode():
            obs_t = torch.from_numpy(obs_flat).float().unsqueeze(0).to(self.device)
            obs_norm = self.obs_normalizer(obs_t)
            raw_action = self.actor(obs_norm).squeeze(0).cpu().numpy()

        # 8. Clip + scale
        raw_action = np.clip(raw_action, -1.0, 1.0)
        self._last_action = raw_action.copy()
        joint_targets = self.default_joint_pos + raw_action * self.ACTION_SCALE

        # Periodic log
        if self._step_count % 10 == 0:
            dist = np.linalg.norm(paper_pose[:2] - self.target_pose[:2])
            logger.info(f"[RLPaperDrag] step={self._step_count} ref_t={ref_t} "
                        f"paper=({paper_pose[0]*100:.1f},{paper_pose[1]*100:.1f})cm "
                        f"θ={np.degrees(paper_pose[2]):.1f}° dist={dist*100:.1f}cm "
                        f"action=[{', '.join(f'{a:.2f}' for a in raw_action)}]")

        self._step_count += 1
        return joint_targets

    # -------------------- ActionModel contract --------------------

    def sample_actions(self, inputs: dict) -> np.ndarray:
        """Phosphobot ActionModel contract: return (seq_len, n_actions).

        For RLPaperDrag seq_len=1 (one-step policy, no action chunking).

        Args:
            inputs: dict with keys:
              - "state": np.ndarray shape (6,) — joint positions in radians
              - "paper_pose": np.ndarray shape (3,) — [x, y, theta]
              - "dt": float — control timestep (default 0.05)
        """
        joint_pos = np.asarray(inputs["state"], dtype=float)
        paper_pose = np.asarray(inputs["paper_pose"], dtype=float)
        dt = float(inputs.get("dt", 0.05))
        targets = self._build_observation_and_act(joint_pos, paper_pose, dt)
        return targets.reshape(1, self.NUM_JOINTS)

    @classmethod
    def fetch_and_get_configuration(cls, model_id: str) -> ModelConfigurationResponse:
        """No video keys (we use camera but don't expose the key via UI);
        no checkpoints list (weights are a local .pt, not HF branches)."""
        return ModelConfigurationResponse(video_keys=[], checkpoints=[])

    @classmethod
    def fetch_and_verify_config(
        cls,
        model_id: str,
        all_cameras: AllCameras,
        robots: List[BaseManipulator],
        cameras_keys_mapping: Optional[dict] = None,
        verify_cameras: bool = True,
    ) -> RLPaperDragSpawnConfig:
        """model_id is a LOCAL directory path (not an HF repo).

        Expected layout:
          {model_id}/best_run20_98pct.pt
          {model_id}/paper_yolo_obb.pt
          {model_id}/so101_nmpc_references.npz
          {model_id}/calibration.json
        """
        model_dir = Path(model_id)
        if not model_dir.is_dir():
            raise ValueError(
                f"RLPaperDrag expects model_id to be a local directory; got {model_id}. "
                f"Create the directory and populate with the 4 required files."
            )
        ckpt = model_dir / "best_run20_98pct.pt"
        yolo = model_dir / "paper_yolo_obb.pt"
        npz = model_dir / "so101_nmpc_references.npz"
        cal = model_dir / "calibration.json"
        missing = [str(p) for p in (ckpt, yolo, npz, cal) if not p.exists()]
        if missing:
            raise ValueError(f"RLPaperDrag missing required files: {missing}")
        if len(robots) != 1:
            raise ValueError(f"RLPaperDrag requires exactly 1 robot; got {len(robots)}")
        # No camera validation — we call get_rgb_frame() by camera_id at runtime.
        return RLPaperDragSpawnConfig(
            model_dir=str(model_dir),
            checkpoint_path=str(ckpt),
            yolo_model_path=str(yolo),
            reference_npz_path=str(npz),
            calibration_json_path=str(cal),
        )

    async def control_loop(
        self,
        control_signal: AIControlSignal,
        robots: List[BaseManipulator],
        model_spawn_config: RLPaperDragSpawnConfig,
        all_cameras: AllCameras,
        prompt: Optional[str] = None,
        fps: int = 20,
        speed: float = 1.0,
        cameras_keys_mapping: Optional[dict] = None,
        angle_format: Literal["degrees", "radians", "other"] = "radians",
        min_angle: Optional[float] = None,
        max_angle: Optional[float] = None,
        **kwargs: Any,  # swallow detect_instruction, selected_camera_id, checkpoint, etc.
    ) -> None:
        """Main 20 Hz control coroutine.

        Follows the gr00t/lerobot pattern: loop until control_signal.stop(),
        reading sensors → model → servo commands each iteration. All in-process.
        """
        # Normalize angle_format ("radians" → "rad" for the bus API)
        unit = {"radians": "rad", "degrees": "degrees", "other": "other"}[angle_format]
        if len(robots) < 1:
            logger.error("[RLPaperDrag] No robots provided; aborting")
            control_signal.stop()
            return
        robot = robots[0]
        period = 1.0 / (fps * speed)
        first = True
        cam_id = model_spawn_config.camera_id

        control_signal.set_running()
        logger.info(f"[RLPaperDrag] control_loop start: fps={fps}, speed={speed}, "
                    f"unit={unit}, camera_id={cam_id}")

        while control_signal.is_in_loop():
            t0 = time.perf_counter()
            try:
                # --- 1. Read joint state (direct motors_bus, ~0.5ms) ---
                joint_pos = np.asarray(robot.read_joints_position(unit="rad"), dtype=float)

                # --- 2. Read camera frame (in-process, cached, ~1ms) ---
                rgb_frame = all_cameras.get_rgb_frame(camera_id=cam_id, resize=None)
                if rgb_frame is None:
                    await asyncio.sleep(period)
                    continue

                # --- 3. YOLO-OBB → paper_pose (BGR input expected by detect_paper_pose) ---
                frame_bgr = rgb_frame[..., ::-1]  # RGB → BGR
                paper_pose = self._detect_paper_pose(frame_bgr)
                if paper_pose is None:
                    # No detection yet — wait for one before starting policy
                    await asyncio.sleep(period)
                    continue

                # --- 4. First step: match reference trajectory for current paper pose ---
                if first:
                    self.reset(paper_pose, joint_pos)
                    first = False

                # --- 5. Policy forward pass ---
                inputs = {"state": joint_pos, "paper_pose": paper_pose, "dt": period}
                actions = self.sample_actions(inputs)  # shape (1, 6)
                target = actions[0]  # (6,)

                # --- 6. Write joint targets to servos (direct motors_bus, ~0.5ms) ---
                robot.write_joint_positions(
                    angles=target.tolist(),
                    unit=unit,
                    max_value=max_angle,
                    min_value=min_angle,
                )

                # --- 7. Reference exhaustion: re-match for current paper pose ---
                if self._step_count >= self._ref_length:
                    logger.info("[RLPaperDrag] Reference exhausted — re-matching")
                    self.reset(paper_pose, joint_pos)

            except Exception as e:
                logger.warning(f"[RLPaperDrag] control_loop exception: {e} — stopping")
                control_signal.stop()
                break

            # --- Pace the loop ---
            elapsed = time.perf_counter() - t0
            if elapsed < period:
                await asyncio.sleep(period - elapsed)

        # --- Cleanup ---
        if self._detection_pub is not None:
            self._detection_pub.close()
        if self._zmq_ctx is not None:
            self._zmq_ctx.term()
        logger.info("[RLPaperDrag] control_loop exited cleanly")
