"""
Dual SO-101 Arm Controller

This module provides a simple interface for controlling two SO-1                # Suggest nearest safe pose
                safe_pose, explanation = find_nearest_safe_pose(position)
                print(f"💡 Suggested safe pose: {safe_pose}")
                print(f"   {explanation}")
                
                # Ask user if they want to proceed with safe pose
                user_response = input("   Use safe pose instead? (y/n): ").lower()
                if user_response == 'y':
                    position = safe_pose
                    print(f"✅ Using safe pose: {position}")
                else:
                    print("❌ Aborted movement due to invalid pose")
                    return False
            else:
                print(f"✅ Pose for arm {robot_id} appears valid")ng direct pose commands through the phosphobot API.
"""
import numpy as np
import httpx
import time
from typing import Optional

# Import workspace validation utilities
try:
    from workspace_check import quick_pose_check, find_nearest_safe_pose
    WORKSPACE_VALIDATION_AVAILABLE = True
except ImportError:
    WORKSPACE_VALIDATION_AVAILABLE = False
    print("⚠️  Workspace validation not available. Run without pose checking.")


class DualSO101Controller:
    """Controller for dual SO-101 robotic arms with pose-based control."""
    
    def __init__(
        self, 
        server_url: str = "http://localhost:80",
        simulation_mode: bool = False,
        enable_workspace_validation: bool = True
    ):
        """
        Initialize the dual arm controller.
        
        Args:
            server_url: URL of the phosphobot server (default: http://localhost:80)
            simulation_mode: If True, initialize for simulation/testing
            enable_workspace_validation: If True, validate poses before movement
        """
        self.server_url = server_url
        self.simulation_mode = simulation_mode
        self.enable_workspace_validation = enable_workspace_validation and WORKSPACE_VALIDATION_AVAILABLE
        
        if simulation_mode:
            # For simulation mode, initialize robot objects directly
            from phosphobot.robot import SO100Robot
            self.left_arm = SO100Robot(side="left", sim_mode="headless")
            self.right_arm = SO100Robot(side="right", sim_mode="headless")
            print("✅ Initialized dual SO-101 controller in simulation mode")
        else:
            # For real robot, use HTTP client
            self.client = httpx.Client(base_url=server_url)
            
            # Verify server connection
            try:
                response = self.client.get("/status")
                response.raise_for_status()
                print(f"✅ Connected to phosphobot server at {server_url}")
            except httpx.RequestError as e:
                print(f"❌ Failed to connect to phosphobot server: {e}")
                raise
        
        if self.enable_workspace_validation:
            print("✅ Workspace validation enabled")
        else:
            print("⚠️  Workspace validation disabled")
    
    def move_arm_absolute_pose(
        self, 
        robot_id: int,
        position: list[float],  # [x, y, z] in meters
        orientation: Optional[list[float]] = None,  # [rx, ry, rz] in degrees
        position_tolerance: float = 0.01,
        orientation_tolerance: float = 5.0,
        max_trials: int = 3,
        validate_workspace: bool = True
    ):
        """
        Move an arm's end effector to an absolute pose (position + orientation).
        
        This controls where the gripper/tool tip is positioned and oriented in 3D space.
        The robot's inverse kinematics automatically calculates the required joint angles.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            position: [x, y, z] end effector coordinates in meters
            orientation: [rx, ry, rz] end effector Euler angles in degrees (optional)
            position_tolerance: Position tolerance in meters
            orientation_tolerance: Orientation tolerance in degrees
            max_trials: Maximum number of attempts
            validate_workspace: If True, check pose validity before moving
        """
        # Workspace validation (if enabled)
        if self.enable_workspace_validation and validate_workspace:
            is_valid, reason = quick_pose_check(position, orientation)
            if not is_valid:
                print(f"❌ Invalid pose for arm {robot_id}: {reason}")
                
                # Suggest nearest safe pose
                safe_pose, explanation = find_nearest_safe_pose(position)
                print(f"💡 Suggested safe pose: {safe_pose}")
                print(f"   {explanation}")
                
                # Ask user if they want to proceed with safe pose
                response = input("   Use safe pose instead? (y/n): ").lower()
                if response == 'y':
                    position = safe_pose
                    print(f"✅ Using safe pose: {position}")
                else:
                    print("❌ Aborted movement due to invalid pose")
                    return False
            else:
                print(f"✅ Pose for arm {robot_id} is valid")
        
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
        Move an arm's end effector relative to its current pose.
        
        This moves the gripper/tool tip by the specified delta amounts from 
        its current position and orientation.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            delta_position: [dx, dy, dz] end effector movement in centimeters
            delta_orientation: [drx, dry, drz] end effector rotation change in degrees
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

    def disconnect(self):
        """Disconnect from the robot(s) and clean up resources."""
        if self.simulation_mode:
            # Cleanup simulation objects
            if hasattr(self, 'left_arm'):
                self.left_arm.disconnect()
            if hasattr(self, 'right_arm'):
                self.right_arm.disconnect()
            print("✅ Disconnected from simulation")
        else:
            # Close HTTP client
            if hasattr(self, 'client'):
                self.client.close()
            print("✅ Disconnected from server")
    
    def validate_pose(self, position: list[float], orientation: Optional[list[float]] = None) -> tuple[bool, str]:
        """
        Validate a pose without moving the robot.
        
        Args:
            position: [x, y, z] coordinates in meters
            orientation: [rx, ry, rz] Euler angles in degrees (optional)
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not self.enable_workspace_validation:
            return True, "Workspace validation disabled"
            
        return quick_pose_check(position, orientation)
