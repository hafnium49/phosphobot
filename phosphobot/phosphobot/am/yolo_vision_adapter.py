#!/usr/bin/env python3
"""
YOLO-based vision system for paper detection.

This module provides a vision system using fine-tuned YOLOv8n for paper detection,
designed as a lightweight replacement for SAM3.

Usage:
    from yolo_vision_adapter import YOLOVisionSystem

    vision = YOLOVisionSystem("models/paper_yolo.pt")
    pose = vision.get_pose(frame)  # Returns [x, y, theta] or None
"""

import math
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np


class YOLOVisionSystem:
    """
    YOLO-based paper detection for SO-101 drag task.

    This is a drop-in replacement for RealVisionSystem/RemoteVisionSystem
    that uses a fine-tuned YOLOv8n model instead of SAM3 or contour detection.

    Key features:
    - Fast inference (~12ms on CPU, ~5ms on GPU)
    - Small model size (<4MB)
    - No external dependencies (HuggingFace, etc.)
    - Trained on occluded paper examples from digital twin
    """

    # Flag to indicate this is a high-rate vision system (80+ Hz)
    # FusionTracker uses this to select appropriate Kalman tuning
    # (SAM3 is low-rate ~2Hz with 400ms latency, YOLO is high-rate)
    is_low_rate = False

    def __init__(
        self,
        model_path: str = "models/paper_yolo.pt",
        conf_threshold: float = 0.5,
        pixels_per_meter: float = 1043.0,
        pixels_per_meter_y: Optional[float] = None,
        camera_center_world: Tuple[float, float] = (0.275, 0.175),
        device: str = "cpu",
        update_interval: int = 1,  # Update every frame (no rate limiting)
        input_bgr: bool = False,  # Set True for real hardware (phosphobot returns BGR)
        camera_rotation: str = "sim",  # "sim" or "real" (for debug logging only)
        angle_offset_deg: float = 180.0,  # OBB angle offset: 180 for sim, 0 for real
        pixel_axes: Optional[list] = None,  # 2x2 axis mapping matrix (calibration-driven)
    ):
        """
        Initialize YOLO vision system.

        Args:
            model_path: Path to trained YOLOv8n model
            conf_threshold: Detection confidence threshold
            pixels_per_meter: Camera calibration (pixels per meter for X axis).
            pixels_per_meter_y: Camera calibration for Y axis (if None, uses pixels_per_meter)
            camera_center_world: Camera center in world coordinates
            device: Inference device ("cpu" or "cuda")
            update_interval: Frames between pose updates (for SAM3 compatibility)
            input_bgr: If True, convert BGR→RGB before inference (for real cameras)
            camera_rotation: Camera mode label for debug logging
            angle_offset_deg: OBB angle transform offset in degrees (180 for sim, 0 for real)
            pixel_axes: 2x2 matrix mapping [dx_m, dy_m] to [delta_world_x, delta_world_y].
                Sim (crossed): [[0,-1],[-1,0]] — dy→world_x, dx→world_y
                Real (direct): [[-1,0],[0,-1]] — dx→world_x, dy→world_y
                If None, defaults to sim convention [[0,-1],[-1,0]].
        """
        from ultralytics import YOLO

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLO model not found: {model_path}")

        self.model = YOLO(str(model_path))
        self.conf_threshold = conf_threshold
        self.device = device

        # Detect model type from filename or model task attribute
        model_path_lower = str(model_path).lower()
        self.is_pose_model = "pose" in model_path_lower or getattr(self.model, 'task', '') == 'pose'
        self.is_obb_model = "obb" in model_path_lower or getattr(self.model, 'task', '') == 'obb'

        # Detect V2 model for algorithm tuning
        self.is_v2_model = "v2" in model_path_lower

        # Camera calibration (supports anisotropic PPM for lens distortion)
        self.pixels_per_meter = pixels_per_meter  # X axis
        self.pixels_per_meter_y = pixels_per_meter_y if pixels_per_meter_y is not None else pixels_per_meter
        self.camera_center_world = np.array(camera_center_world)

        # Paper dimensions (A5: 148mm x 210mm)
        self.paper_half_w = 0.074  # Short edge half
        self.paper_half_h = 0.105  # Long edge half

        # Optional workspace bounds for filtering false detections (set externally)
        # Format: {"bounds_x": [min, max], "bounds_y": [min, max]}
        self.workspace_bounds = None

        # SAM3-compatible sequence tracking
        self.update_interval = update_interval
        self.frame_count = 0
        self.seq = 0
        self.last_pose = None
        self.initial_pose = None  # Set once via set_initial_pose(), used for 90° disambiguation
        self.last_detection_time = 0

        # Exponentially-weighted theta history for disambiguation
        # Each entry: (theta, confidence, timestamp)
        # Uses exponential decay: weight = exp(-lambda * age) * confidence
        self.theta_history = []
        self.decay_lambda = 10.0  # Decay rate: e^(-10*dt) → 50% at 70ms, 10% at 230ms

        # Target pose for compatibility
        self.target_pose_robot = np.array([0.275, 0.175, 1.57])

        # Input format (BGR for real hardware, RGB for simulation)
        self.input_bgr = input_bgr

        # Camera coordinate frame transform
        self.camera_rotation = camera_rotation
        self.angle_offset_deg = angle_offset_deg

        # Axis mapping matrix: maps [dx_m, dy_m] → [delta_world_x, delta_world_y]
        # Sim (crossed axes from xyaxes="0 -1 0 1 0 0"): [[0,-1],[-1,0]]
        # Real (direct axes): [[-1,0],[0,-1]]
        if pixel_axes is not None:
            self.pixel_axes = np.array(pixel_axes, dtype=float)
        else:
            self.pixel_axes = np.array([[0, -1], [-1, 0]], dtype=float)  # SIM default

        # Masker attribute for compatibility
        self.masker = None

        # Debug logging
        self.debug_logging = False
        self._debug_frame_count = 0

        print(f"[YOLOVision] Loaded model: {model_path}")
        print(f"[YOLOVision] Device: {device}, Conf: {conf_threshold}")
        if self.is_pose_model:
            print(f"[YOLOVision] POSE mode: Keypoint-based orientation (no ambiguity)")
        elif self.is_obb_model:
            print(f"[YOLOVision] OBB mode: Direct rotation output (no minAreaRect)")

    def pixel_to_world(self, px: float, py: float, img_w: int = 640, img_h: int = 480) -> Tuple[float, float]:
        """Convert pixel coordinates to world coordinates.

        Uses a 2x2 axis mapping matrix (pixel_axes) from calibration:
          world_x = center[0] + M[0,0]*dx_m + M[0,1]*dy_m
          world_y = center[1] + M[1,0]*dx_m + M[1,1]*dy_m

        Sim (crossed axes): M = [[0,-1],[-1,0]] — dy→world_x, dx→world_y
        Real (direct axes): M = [[-1,0],[0,-1]] — dx→world_x, dy→world_y
        Same formula for both — only M values differ in calibration.
        """
        # Offset from image center
        dx_px = px - img_w / 2
        dy_px = py - img_h / 2

        # Convert pixel offsets to meters
        dx_m = dx_px / self.pixels_per_meter      # Pixel X axis PPM
        dy_m = dy_px / self.pixels_per_meter_y     # Pixel Y axis PPM

        # Camera axes → world axes via calibration matrix
        M = self.pixel_axes
        world_x = self.camera_center_world[0] + M[0, 0] * dx_m + M[0, 1] * dy_m
        world_y = self.camera_center_world[1] + M[1, 0] * dx_m + M[1, 1] * dy_m

        return world_x, world_y

    def estimate_orientation(self, frame: np.ndarray, box: np.ndarray) -> float:
        """
        Estimate paper orientation from detected bounding box.

        Uses contour analysis within the detected region to find the
        paper's long edge orientation.

        Args:
            frame: RGB image
            box: YOLO bounding box [x1, y1, x2, y2]

        Returns:
            Orientation angle in radians [-pi, pi]
        """
        x1, y1, x2, y2 = map(int, box)

        # Pad the box slightly
        pad = 5
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(frame.shape[1], x2 + pad)
        y2 = min(frame.shape[0], y2 + pad)

        # Extract ROI
        roi = frame[y1:y2, x1:x2]

        if roi.size == 0:
            return 0.0

        # Convert to grayscale
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        else:
            gray = roi

        # Threshold to find paper (bright object)
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        # Get largest contour
        largest = max(contours, key=cv2.contourArea)

        if cv2.contourArea(largest) < 100:
            return 0.0

        # Fit minimum area rectangle
        rect = cv2.minAreaRect(largest)
        _, (w, h), angle = rect

        # Compute orientation (long edge angle)
        # OpenCV angle is in degrees, -90 to 0
        if w < h:
            angle_rad = math.radians(angle + 90)
        else:
            angle_rad = math.radians(angle)

        # Normalize to [-pi, pi]
        while angle_rad > math.pi:
            angle_rad -= 2 * math.pi
        while angle_rad < -math.pi:
            angle_rad += 2 * math.pi

        # Transform angle from camera frame to MuJoCo frame
        # Camera has xyaxes="0 -1 0 1 0 0" which includes reflection
        angle_rad = -angle_rad - math.pi

        # Re-normalize
        while angle_rad > math.pi:
            angle_rad -= 2 * math.pi
        while angle_rad < -math.pi:
            angle_rad += 2 * math.pi

        return angle_rad

    def detect_paper_pose(self, frame: np.ndarray, link_positions=None) -> Optional[np.ndarray]:
        """
        Detect paper pose from camera frame.

        Args:
            frame: Image (H, W, 3) - RGB or BGR depending on input_bgr setting
            link_positions: Ignored (for API compatibility)

        Returns:
            Pose array [x, y, theta] or None if no detection
        """
        if frame is None:
            return None

        # Axis direction is encoded in signed PPM values (no code branching needed):
        #   Sim (positive PPM): image RIGHT = world -Y, UP = world +X
        #   Real (negative PPM): image RIGHT = world +Y, UP = world -X

        # NOTE: Ultralytics YOLO expects BGR images (trained on OpenCV-loaded images).
        # Do NOT convert BGR→RGB - ultralytics handles color space internally.
        # The input_bgr flag is now only used for documentation/future compatibility.

        # Run YOLO inference
        results = self.model(frame, verbose=False, device=self.device, conf=self.conf_threshold)[0]

        # Check for Pose results (keypoint detection)
        if self.is_pose_model:
            if hasattr(results, 'keypoints') and results.keypoints is not None and len(results.keypoints) > 0:
                return self._detect_from_pose(results, frame.shape[1], frame.shape[0])
            return None  # No pose detection this frame

        # Check for OBB results (oriented bounding boxes with rotation)
        if self.is_obb_model:
            # OBB model: only use OBB results, no fallback to boxes
            if hasattr(results, 'obb') and results.obb is not None and len(results.obb) > 0:
                return self._detect_from_obb(results, frame.shape[1], frame.shape[0])
            return None  # No OBB detection this frame

        # Standard detection model: use bounding boxes
        return self._detect_from_bbox(results, frame)

    def _detect_from_obb(self, results, img_w: int, img_h: int) -> Optional[np.ndarray]:
        """
        Extract pose from OBB (Oriented Bounding Box) results.

        Uses xywhr theta with 90°+180° disambiguation:
        - Raw theta is transformed from camera to world coordinates
        - 4 orientation variants (0°, 90°, 180°, 270°) are generated
        - The closest variant to the reference pose is selected
        """
        # Get detections sorted by confidence (highest first)
        confs = results.obb.conf.cpu().numpy()
        sorted_indices = np.argsort(confs)[::-1]  # Descending confidence

        # Periodic detection diagnostics (every 50 frames)
        self._debug_frame_count = getattr(self, '_debug_frame_count', 0) + 1
        if self._debug_frame_count % 50 == 1 and len(confs) > 0:
            det_info = []
            for i in sorted_indices[:5]:
                obb_d = results.obb.xywhr[i].cpu().numpy()
                wx, wy = self.pixel_to_world(obb_d[0], obb_d[1], img_w, img_h)
                bounds_tag = ""
                if self.workspace_bounds is not None:
                    bx = self.workspace_bounds.get("bounds_x", [-1e6, 1e6])
                    by = self.workspace_bounds.get("bounds_y", [-1e6, 1e6])
                    in_b = bx[0] <= wx <= bx[1] and by[0] <= wy <= by[1]
                    bounds_tag = " IN" if in_b else " OUT"
                det_info.append(f"conf={confs[i]:.3f} px=({obb_d[0]:.0f},{obb_d[1]:.0f}) world=({wx*100:.1f},{wy*100:.1f})cm{bounds_tag}")
            print(f"[YOLO] {len(confs)} det (img {img_w}x{img_h}): {', '.join(det_info)}")

        # Find best detection that passes filters (confidence + optional bounds)
        best_idx = None
        for idx in sorted_indices:
            if confs[idx] < self.conf_threshold:
                break  # All remaining have lower confidence

            # Check workspace bounds if set
            if self.workspace_bounds is not None:
                obb_tmp = results.obb.xywhr[idx].cpu().numpy()
                x_tmp, y_tmp = self.pixel_to_world(obb_tmp[0], obb_tmp[1], img_w, img_h)
                bx = self.workspace_bounds.get("bounds_x", [-1e6, 1e6])
                by = self.workspace_bounds.get("bounds_y", [-1e6, 1e6])
                if not (bx[0] <= x_tmp <= bx[1] and by[0] <= y_tmp <= by[1]):
                    continue  # Skip out-of-bounds detection

            best_idx = idx
            break

        if best_idx is None:
            return None

        best_conf = confs[best_idx]

        # OBB format: [cx, cy, w, h, rotation] in pixels, rotation in radians
        obb_data = results.obb.xywhr[best_idx].cpu().numpy()
        cx_px, cy_px, w_px, h_px, theta_rad = obb_data

        # Convert center to world coordinates
        x_world, y_world = self.pixel_to_world(cx_px, cy_px, img_w, img_h)

        # --- TRANSFORM OBB THETA TO WORLD COORDINATES ---
        # The OBB model's theta represents the width axis in camera coords
        camera_angle_deg = np.degrees(theta_rad)
        # angle_offset_deg: 180 for sim (positive PPM), 0 for real (negative PPM)
        theta_world = np.radians(-(camera_angle_deg + self.angle_offset_deg))

        # Normalize to [-pi, pi]
        def normalize_angle(a):
            while a > math.pi:
                a -= 2 * math.pi
            while a < -math.pi:
                a += 2 * math.pi
            return a

        theta_world = normalize_angle(theta_world)

        # --- EXPONENTIALLY-WEIGHTED HISTORY DISAMBIGUATION ---
        # OBB has ambiguity near axis-aligned poses. Measurements show:
        #   - Near 0° (±15°): conf ~0.35-0.44, large errors (~80°)
        #   - Diagonal (30°-75°): conf ~0.55-0.78, small errors (<7°)
        #   - Near 90°: conf ~0.46, small errors (~6°)
        #
        # Strategy: Use exponentially-weighted history for reference.
        # - weight_i = exp(-lambda * age_i) * confidence_i
        # - Recent high-confidence frames dominate
        # - Smooth decay (no abrupt window edge)
        # - Falls back to initial_pose if history insufficient

        current_time = time.time()

        # --- OPTIMIZATION: Adaptive Decay Lambda ---
        # Increase decay (shorter memory) when history has high variance
        # This helps V2 forget bad high-confidence detections faster
        effective_lambda = self.decay_lambda
        if len(self.theta_history) >= 5:
            recent_angles = [t for t, c, ts in self.theta_history[-10:]]
            # Circular variance: 1 - |mean of unit vectors|, range [0, 1]
            variance = 1.0 - abs(np.mean([np.exp(1j * a) for a in recent_angles]))
            # V1 typical: variance ~0.1 → lambda ~13
            # V2 with jumps: variance ~0.5 → lambda ~25 (faster forgetting)
            effective_lambda = self.decay_lambda * (1.0 + 3.0 * variance)

        # Compute exponentially-weighted history reference using circular mean
        reference_theta = None
        if len(self.theta_history) > 0:
            weighted_sum = 0j  # Complex number for circular mean
            total_weight = 0.0

            # Pre-compute history mean for consistency check
            history_mean = None
            if len(self.theta_history) >= 3:
                recent = self.theta_history[-5:]
                history_mean = np.angle(np.mean([np.exp(1j * t) for t, c, ts in recent]))

            for hist_theta, hist_conf, hist_time in self.theta_history:
                age = current_time - hist_time
                # Exponential decay: more recent = higher weight
                time_weight = math.exp(-effective_lambda * age)

                # --- OPTIMIZATION: Consistency-Based Confidence Downweighting ---
                # Downweight high-confidence detections that disagree with recent history
                # This prevents V2's wrong high-conf detections from corrupting history
                effective_conf = hist_conf
                if history_mean is not None:
                    consistency_err = abs((hist_theta - history_mean + math.pi) % (2 * math.pi) - math.pi)
                    # If high confidence but inconsistent (>30° from history mean), downweight
                    if consistency_err > 0.5 and hist_conf > 0.7:
                        effective_conf = hist_conf * 0.3

                # Combined weight: time decay × (possibly adjusted) confidence
                weight = time_weight * effective_conf

                weighted_sum += weight * np.exp(1j * hist_theta)
                total_weight += weight

            if total_weight > 0.1:  # Minimum weight threshold
                reference_theta = np.angle(weighted_sum)

        # Fallback to initial_pose if no sufficient history
        if reference_theta is None and self.initial_pose is not None:
            reference_theta = self.initial_pose[2]

        if reference_theta is not None:
            # Generate all 4 possible orientations (covers 0° and 90° offset cases)
            variants = [
                theta_world,
                normalize_angle(theta_world + math.pi / 2),
                normalize_angle(theta_world + math.pi),
                normalize_angle(theta_world + 3 * math.pi / 2),
            ]

            # Pick the one closest to reference
            errors = []
            for v in variants:
                diff = (v - reference_theta + math.pi) % (2 * math.pi) - math.pi
                errors.append(abs(diff))

            best_idx = np.argmin(errors)
            theta_world = variants[best_idx]

        # --- OPTIMIZATION: Velocity-Based Outlier Rejection ---
        # Don't add to history if angular velocity is impossibly high
        # This prevents sudden 90° jumps from corrupting history
        add_to_history = True
        if hasattr(self, '_last_theta') and hasattr(self, '_last_time'):
            dt = current_time - self._last_time
            if dt > 0.001:  # Avoid division by zero
                angular_vel = abs((theta_world - self._last_theta + math.pi) % (2 * math.pi) - math.pi) / dt
                # Max expected: ~5 rad/s for paper rotation, use 15 as safety margin
                if angular_vel > 15.0:
                    add_to_history = False  # Likely a bad detection, don't corrupt history

        # Store for next velocity check
        self._last_theta = theta_world
        self._last_time = current_time

        # Store in history (after disambiguation) with confidence and timestamp
        if add_to_history:
            self.theta_history.append((theta_world, best_conf, current_time))

        # Prune old entries (older than 500ms - negligible weight anyway)
        cutoff_time = current_time - 0.5
        self.theta_history = [(t, c, ts) for t, c, ts in self.theta_history if ts > cutoff_time]

        pose = np.array([x_world, y_world, theta_world])
        self.last_pose = pose.copy()
        self.last_detection_time = current_time

        return pose

    def _detect_from_pose(self, results, img_w: int, img_h: int) -> Optional[np.ndarray]:
        """
        Extract pose from keypoint detection results (YOLO-Pose).

        Uses the E1->E2 vector (from canonical top edge to bottom edge) to compute
        orientation. No history tracking needed - canonical visual sorting eliminates
        ambiguity at the dataset level.

        Keypoints:
            0: Paper center
            1: Primary short edge midpoint (canonical: higher in image)
            2: Secondary short edge midpoint
        """
        # Get highest confidence detection
        confs = results.boxes.conf.cpu().numpy()
        best_idx = np.argmax(confs)
        best_conf = confs[best_idx]

        if best_conf < self.conf_threshold:
            return None

        # Extract keypoints: shape is (N, K, 2) or (N, K, 3) with visibility
        keypoints = results.keypoints.xy[best_idx].cpu().numpy()  # (3, 2)

        # Keypoint 0: Center, Keypoints 1&2: Edge midpoints (may need sorting)
        center_px = keypoints[0]  # (x, y)
        raw_edge1_px = keypoints[1]
        raw_edge2_px = keypoints[2]

        # Check for invalid keypoints (zero means not detected)
        if np.allclose(center_px, 0) or np.allclose(raw_edge1_px, 0) or np.allclose(raw_edge2_px, 0):
            return None

        # --- RUNTIME CANONICAL SORTING ---
        # Enforce canonical ordering: edge1 = smaller Y (higher in image)
        # The model might not output keypoints in the same order as training labels,
        # so we apply the same sorting rule used during dataset generation.
        if raw_edge1_px[1] < raw_edge2_px[1]:
            edge1_px, edge2_px = raw_edge1_px, raw_edge2_px
        elif raw_edge1_px[1] > raw_edge2_px[1]:
            edge1_px, edge2_px = raw_edge2_px, raw_edge1_px
        else:
            # Tiebreaker: larger X wins as edge1
            if raw_edge1_px[0] >= raw_edge2_px[0]:
                edge1_px, edge2_px = raw_edge1_px, raw_edge2_px
            else:
                edge1_px, edge2_px = raw_edge2_px, raw_edge1_px

        # Convert center to world coordinates
        x_world, y_world = self.pixel_to_world(center_px[0], center_px[1], img_w, img_h)

        # --- Compute orientation from E1->E2 vector ---
        # The vector from edge1 to edge2 points along the paper's long axis
        # (perpendicular to the short edges)
        vec_px = edge2_px - edge1_px  # In pixel coordinates

        # Pixel coordinates: +X is right, +Y is down
        # atan2 gives angle from +X axis, CCW positive
        theta_camera = math.atan2(vec_px[1], vec_px[0])

        # Transform from camera frame to world frame
        #
        # The camera coordinate system (from generate_yolo_dataset.py):
        #   cam_x = -world_y, cam_y = world_x
        #   px = img_w/2 + cam_x * ppm
        #   py = img_h/2 - cam_y * ppm  (y-flip for image coords)
        #
        # After working through the math:
        #   theta_pixel = atan2(-sin(theta_world), cos(theta_world)) = -theta_world
        #
        # Therefore: theta_world = -theta_camera
        theta_world = -theta_camera

        # Normalize to [-pi, pi]
        while theta_world > math.pi:
            theta_world -= 2 * math.pi
        while theta_world < -math.pi:
            theta_world += 2 * math.pi

        # --- NO HISTORY TRACKING NEEDED ---
        # The canonical visual sorting in the dataset eliminates the 90/180 degree
        # ambiguity. The model learns to consistently identify the "visually higher"
        # edge as Point 1, so the E1->E2 vector always points in a consistent direction.

        # Debug logging (controlled by self.debug_logging)
        if self.debug_logging:
            self._debug_frame_count += 1
            # Only print every 20th frame to avoid flooding
            if self._debug_frame_count % 20 == 1:
                # Check if kpt1 is actually "above" kpt2 in image (smaller Y = higher)
                kpt1_above = edge1_px[1] < edge2_px[1]
                sort_status = "OK" if kpt1_above else "SWAPPED!"
                print(f"[POSE-DEBUG #{self._debug_frame_count}] kpt0=({center_px[0]:.0f},{center_px[1]:.0f}) kpt1=({edge1_px[0]:.0f},{edge1_px[1]:.0f}) kpt2=({edge2_px[0]:.0f},{edge2_px[1]:.0f}) [{sort_status}]")
                print(f"[POSE-DEBUG] vec_px=({vec_px[0]:.1f}, {vec_px[1]:.1f}) -> theta_cam={np.degrees(theta_camera):.1f}° -> theta_world={np.degrees(theta_world):.1f}°")

        current_time = time.time()
        pose = np.array([x_world, y_world, theta_world])
        self.last_pose = pose.copy()
        self.last_detection_time = current_time

        return pose

    def _detect_from_bbox(self, results, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract pose from standard detection results (axis-aligned bounding boxes).

        Uses minAreaRect post-processing to estimate orientation,
        which has inherent 90° ambiguity.
        """
        if len(results.boxes) == 0:
            return None

        # Get highest confidence detection
        confs = results.boxes.conf.cpu().numpy()
        best_idx = np.argmax(confs)
        best_conf = confs[best_idx]

        if best_conf < self.conf_threshold:
            return None

        # Get bounding box
        box = results.boxes.xyxy[best_idx].cpu().numpy()
        x1, y1, x2, y2 = box

        # Compute center in pixels
        cx_px = (x1 + x2) / 2
        cy_px = (y1 + y2) / 2

        # Convert to world coordinates
        x_world, y_world = self.pixel_to_world(cx_px, cy_px, frame.shape[1], frame.shape[0])

        # Estimate orientation using minAreaRect (has 90° ambiguity)
        theta = self.estimate_orientation(frame, box)

        pose = np.array([x_world, y_world, theta])
        self.last_pose = pose.copy()
        self.last_detection_time = time.time()

        return pose

    def get_pose(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Alias for detect_paper_pose (for API compatibility)."""
        return self.detect_paper_pose(frame)

    # NOTE: get_pose_with_seq() was REMOVED because it caused FusionTracker to treat
    # YOLO as a SAM3-like async system. YOLO should run synchronously through
    # _update_centroid_based() which calls detect_paper_pose() on each frame.

    def set_initial_pose(self, pose: np.ndarray):
        """Set initial pose for 90°/180° ambiguity resolution."""
        self.last_pose = pose.copy()
        self.initial_pose = pose.copy()  # Never updated after this
        self.theta_history = []  # Clear history on new initial pose
        # Reset velocity tracking for outlier rejection
        self._last_theta = pose[2]
        self._last_time = time.time()
        print(f"[YOLOVision] Initial pose set: ({pose[0]:.3f}, {pose[1]:.3f}, {np.degrees(pose[2]):.1f}°)")

    def reset(self):
        """Reset state."""
        self.frame_count = 0
        self.seq = 0
        self.last_pose = None
        self.theta_history = []  # Clear history on reset
        # Reset velocity tracking for outlier rejection
        if hasattr(self, '_last_theta'):
            del self._last_theta
        if hasattr(self, '_last_time'):
            del self._last_time


def test_yolo_vision():
    """Test YOLO vision system with a sample image."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python yolo_vision_adapter.py <image_path>")
        print("       python yolo_vision_adapter.py debug_images/published_frame_0.jpg")
        return

    image_path = sys.argv[1]

    # Load image
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"Failed to load image: {image_path}")
        return

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Initialize vision
    try:
        vision = YOLOVisionSystem("models/paper_yolo.pt")
    except FileNotFoundError:
        print("Model not found. Train first with:")
        print("  uv run python tools/train_yolo_paper.py --data datasets/paper_yolo/data.yaml")
        return

    # Detect
    t0 = time.time()
    pose = vision.detect_paper_pose(frame_rgb)
    dt = (time.time() - t0) * 1000

    if pose is not None:
        print(f"Detected pose: x={pose[0]:.3f}, y={pose[1]:.3f}, theta={np.degrees(pose[2]):.1f}°")
        print(f"Inference time: {dt:.1f}ms")
    else:
        print("No paper detected")
        print(f"Inference time: {dt:.1f}ms")


if __name__ == "__main__":
    test_yolo_vision()
