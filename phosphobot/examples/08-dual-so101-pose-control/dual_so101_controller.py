"""
Dual SO-101 Arm Controller

This module provides a simple interface for controlling two SO-101 robotic arms
using direct pose commands through the phosphobot API.
"""
import numpy as np
import httpx
import time
from typing import Optional

# Import workspace validation utilities (optional)
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
        except httpx.RequestError as e:
            print(f"❌ Failed to move arm {robot_id}: {e}")
            return None
    
    def move_arm_relative_pose(
        self, 
        robot_id: int,
        delta_position: list[float],  # [dx, dy, dz] in centimeters
        delta_orientation: Optional[list[float]] = None,  # [drx, dry, drz] in degrees
        position_tolerance: float = 0.01,
        orientation_tolerance: float = 5.0,
        max_trials: int = 3
    ):
        """
        Move an arm's end effector relative to its current pose.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            delta_position: [dx, dy, dz] relative movement in centimeters
            delta_orientation: [drx, dry, drz] relative rotation in degrees (optional)
            position_tolerance: Position tolerance in meters
            orientation_tolerance: Orientation tolerance in degrees
            max_trials: Maximum number of attempts
        """
        # Convert centimeters to meters for the API
        delta_position_m = [d / 100.0 for d in delta_position]
        
        payload = {
            "dx": delta_position_m[0],
            "dy": delta_position_m[1],
            "dz": delta_position_m[2],
            "position_tolerance": position_tolerance,
            "orientation_tolerance": orientation_tolerance,
            "max_trials": max_trials
        }
        
        if delta_orientation:
            payload.update({
                "drx": delta_orientation[0],
                "dry": delta_orientation[1],
                "drz": delta_orientation[2]
            })
        
        try:
            response = self.client.post(
                "/move/relative",
                json=payload,
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            print(f"✅ Arm {robot_id} moved by {delta_position} cm")
            return response.json()
        except httpx.RequestError as e:
            print(f"❌ Failed to move arm {robot_id} relatively: {e}")
            return None
    
    def control_gripper(self, robot_id: int, gripper_value: float):
        """
        Control the gripper of a specific arm.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            gripper_value: 0.0 = closed, 1.0 = open
        """
        try:
            response = self.client.post(
                "/gripper",
                json={"value": gripper_value},
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            state = "open" if gripper_value > 0.5 else "closed"
            print(f"✅ Arm {robot_id} gripper {state}")
            return response.json()
        except httpx.RequestError as e:
            print(f"❌ Failed to control gripper for arm {robot_id}: {e}")
            return None
    
    def get_arm_pose(self, robot_id: int):
        """
        Get the current pose of an arm's end effector.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            
        Returns:
            dict: Current pose information
        """
        try:
            response = self.client.get(
                "/pose",
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"❌ Failed to get pose for arm {robot_id}: {e}")
            return None
    
    def get_current_pose(self, robot_id: int):
        """
        Get the current pose of an arm's end effector.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            
        Returns:
            list: Current [x, y, z] position in meters
        """
        pose_data = self.get_arm_pose(robot_id)
        if pose_data:
            # Extract position from pose data
            return [pose_data.get('x', 0), pose_data.get('y', 0), pose_data.get('z', 0)]
        return [0, 0, 0]
    
    def stop_arm(self, robot_id: int):
        """
        Emergency stop for a specific arm.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
        """
        try:
            response = self.client.post(
                "/stop",
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            print(f"🛑 Arm {robot_id} stopped")
            return response.json()
        except httpx.RequestError as e:
            print(f"❌ Failed to stop arm {robot_id}: {e}")
            return None
    
    def get_robot_status(self):
        """
        Get the status of all connected robots.
        
        Returns:
            dict: Status information for all robots
        """
        try:
            response = self.client.get("/status")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"❌ Failed to get robot status: {e}")
            return None
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'client'):
            self.client.close()
        print("🔌 Controller disconnected")


# Convenience functions for common operations
def initialize_controller(**kwargs):
    """Initialize and return a dual arm controller."""
    return DualSO101Controller(**kwargs)

def demo_basic_movement():
    """Simple demo of basic dual arm movements."""
    print("🤖 Dual SO-101 Basic Movement Demo")
    
    # Initialize controller
    controller = DualSO101Controller()
    
    try:
        # Move both arms to home positions
        print("\n📍 Moving to home positions...")
        controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20])  # Left arm
        controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20])  # Right arm
        
        time.sleep(2)
        
        # Open grippers
        print("\n✋ Opening grippers...")
        controller.control_gripper(0, 1.0)  # Open left gripper
        controller.control_gripper(1, 1.0)  # Open right gripper
        
        time.sleep(1)
        
        # Move arms to different positions
        print("\n🏃 Moving to new positions...")
        controller.move_arm_absolute_pose(0, [0.30, 0.20, 0.15])  # Left forward
        controller.move_arm_absolute_pose(1, [0.30, -0.20, 0.15])  # Right forward
        
        time.sleep(2)
        
        # Close grippers
        print("\n✊ Closing grippers...")
        controller.control_gripper(0, 0.0)  # Close left gripper
        controller.control_gripper(1, 0.0)  # Close right gripper
        
        print("\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    finally:
        controller.close()


if __name__ == "__main__":
    demo_basic_movement()
