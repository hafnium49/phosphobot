"""
Dual SO-101 Arm Controller

This module provides a simple interface for controlling two SO-101 robotic arms
using direct pose commands through the phosphobot API.
"""
import numpy as np
import httpx
import time
from typing import Optional


class DualSO101Controller:
    """Controller for dual SO-101 robotic arms with pose-based control."""
    
    def __init__(self, server_url: str = "http://localhost:80"):
        """
        Initialize the dual arm controller.
        
        Args:
            server_url: URL of the phosphobot server (default: http://localhost:80)
        """
        self.server_url = server_url
        self.client = httpx.Client(base_url=server_url)
        
        # Verify server connection
        try:
            response = self.client.get("/status")
            response.raise_for_status()
            print(f"✅ Connected to phosphobot server at {server_url}")
        except httpx.RequestError as e:
            print(f"❌ Failed to connect to phosphobot server: {e}")
            raise
    
    def move_arm_absolute_pose(
        self, 
        robot_id: int,
        position: list[float],  # [x, y, z] in meters
        orientation: Optional[list[float]] = None,  # [rx, ry, rz] in degrees
        position_tolerance: float = 0.01,
        orientation_tolerance: float = 5.0,
        max_trials: int = 3
    ):
        """
        Move an arm to an absolute pose (position + orientation).
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            position: [x, y, z] coordinates in meters
            orientation: [rx, ry, rz] Euler angles in degrees (optional)
            position_tolerance: Position tolerance in meters
            orientation_tolerance: Orientation tolerance in degrees
            max_trials: Maximum number of attempts
        """
        payload = {
            "x": position[0],
            "y": position[1], 
            "z": position[2],
            "position_tolerance": position_tolerance,
            "orientation_tolerance": orientation_tolerance,
            "max_trials": max_trials
        }
        
        if orientation:
            payload.update({
                "rx": orientation[0],
                "ry": orientation[1], 
                "rz": orientation[2]
            })
        
        try:
            response = self.client.post(
                "/move/absolute",
                json=payload,
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            print(f"✅ Arm {robot_id} moved to position {position}")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to move arm {robot_id}: {e.response.text}")
            raise
    
    def move_arm_relative_pose(
        self,
        robot_id: int,
        delta_position: list[float],  # [dx, dy, dz] in centimeters
        delta_orientation: Optional[list[float]] = None,  # [drx, dry, drz] in degrees
        gripper_open: Optional[float] = None  # 0.0 = closed, 1.0 = open
    ):
        """
        Move an arm relative to its current pose.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            delta_position: [dx, dy, dz] relative movement in centimeters
            delta_orientation: [drx, dry, drz] relative rotation in degrees
            gripper_open: Gripper state (0.0-1.0)
        """
        payload = {
            "x": delta_position[0],
            "y": delta_position[1],
            "z": delta_position[2]
        }
        
        if delta_orientation:
            payload.update({
                "rx": delta_orientation[0],
                "ry": delta_orientation[1],
                "rz": delta_orientation[2]
            })
            
        if gripper_open is not None:
            payload["open"] = gripper_open
        
        try:
            response = self.client.post(
                "/move/relative", 
                json=payload,
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            print(f"✅ Arm {robot_id} moved relatively by {delta_position}")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to move arm {robot_id} relatively: {e.response.text}")
            raise

    def control_gripper(self, robot_id: int, open_command: float):
        """
        Control gripper directly.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm  
            open_command: 0.0 = fully closed, 1.0 = fully open
        """
        try:
            response = self.client.post(
                "/gripper/control",
                json={"open_command": open_command},
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            state = "open" if open_command > 0.5 else "closed"
            print(f"✅ Arm {robot_id} gripper {state}")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to control gripper for arm {robot_id}: {e.response.text}")
            raise

    def get_current_pose(self, robot_id: int):
        """Get current pose of the arm."""
        try:
            response = self.client.get(
                "/kinematics/forward", 
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to get pose for arm {robot_id}: {e.response.text}")
            raise

    def get_robot_status(self):
        """Get status of all connected robots."""
        try:
            response = self.client.get("/status")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to get robot status: {e.response.text}")
            raise

    def close(self):
        """Close the HTTP client."""
        self.client.close()
