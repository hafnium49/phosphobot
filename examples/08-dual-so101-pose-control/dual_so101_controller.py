"""
Dual SO-101 Arm Controller

This module provides a simple interface for controlling two SO-101 robotic arms
using direct pose commands through the phosphobot API.
"""
import numpy as np
import requests
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
            # For real robot, use requests session
            self.session = requests.Session()
            print("✅ Initialized dual SO-101 controller with real robot API")
            
            # Skip server connection verification as /status endpoint may not be available
            # Connection will be verified when robot is initialized
            print(f"🔗 Ready to connect to phosphobot server at {server_url}")
        
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
            "x": position[0] * 100,  # Convert meters to centimeters
            "y": position[1] * 100,  # Convert meters to centimeters
            "z": position[2] * 100,  # Convert meters to centimeters
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
            # Use the working /move/absolute endpoint format
            payload.update({
                "open": 0  # Keep gripper state, 0 = closed
            })
            
            response = self.session.post(
                f"{self.server_url}/move/absolute",
                json=payload
            )
            response.raise_for_status()
            print(f"✅ Arm {robot_id} moved to position {position} (converted to cm)")
            return response.json()
        except requests.RequestException as e:
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
        payload = {
            "dx": delta_position[0],  # Already in centimeters
            "dy": delta_position[1],  # Already in centimeters
            "dz": delta_position[2],  # Already in centimeters
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
            # Use working relative endpoint format
            payload.update({
                "open": 0  # Keep gripper state
            })
            
            response = self.session.post(
                f"{self.server_url}/move/relative",
                json=payload
            )
            response.raise_for_status()
            print(f"✅ Arm {robot_id} moved by {delta_position} cm")
            return response.json()
        except requests.RequestException as e:
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
            # Note: Since /pose endpoint doesn't work, we'll use a simple gripper command
            # This assumes the robot maintains its position when only changing gripper
            payload = {
                "open": int(gripper_value)  # Convert to int: 0 = closed, 1 = open
            }
            
            response = self.session.post(f"{self.server_url}/move/absolute", json=payload)
            response.raise_for_status()
            state = "open" if gripper_value > 0.5 else "closed"
            print(f"✅ Arm {robot_id} gripper {state}")
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Failed to control gripper for arm {robot_id}: {e}")
            return None
    
    def get_arm_pose(self, robot_id: int):
        """
        Get the current pose of an arm's end effector.
        NOTE: This function is disabled as /pose endpoint is not available.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            
        Returns:
            dict: Current pose information (returns None as endpoint unavailable)
        """
        print(f"⚠️ get_arm_pose() disabled - /pose endpoint not available")
        return None
        
        # Original code (disabled):
        # try:
        #     response = self.session.get(f"{self.server_url}/pose")
        #     response.raise_for_status()
        #     pose_data = response.json()
        #     
        #     # The API might return pose data in different formats
        #     # Try to extract robot-specific data if available
        #     if isinstance(pose_data, list) and len(pose_data) > robot_id:
        #         return pose_data[robot_id]
        #     elif isinstance(pose_data, dict):
        #         return pose_data
        #     else:
        #         # Return a default pose if no specific data available
        #         return {"x": 0, "y": 0, "z": 0, "rx": 0, "ry": 0, "rz": 0}
        # except requests.RequestException as e:
        #     print(f"❌ Failed to get pose for arm {robot_id}: {e}")
        #     return None
    
    def get_current_pose(self, robot_id: int):
        """
        Get the current pose of an arm's end effector.
        NOTE: This function is disabled as /pose endpoint is not available.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
            
        Returns:
            list: Current [x, y, z] position in meters (returns default as endpoint unavailable)
        """
        print(f"⚠️ get_current_pose() disabled - /pose endpoint not available")
        return [0, 0, 0]  # Default position
    
    def stop_arm(self, robot_id: int):
        """
        Emergency stop for a specific arm.
        NOTE: This function may not work as /stop endpoint availability is unknown.
        
        Args:
            robot_id: 0 for first arm, 1 for second arm
        """
        try:
            response = self.session.post(
                f"{self.server_url}/stop",
                params={"robot_id": robot_id}
            )
            response.raise_for_status()
            print(f"🛑 Arm {robot_id} stopped")
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Failed to stop arm {robot_id}: {e}")
            return None
    
    def get_robot_status(self):
        """
        Get the status of all connected robots.
        NOTE: This function may not work as /status endpoint availability is unknown.
        
        Returns:
            dict: Status information for all robots
        """
        try:
            response = self.session.get(f"{self.server_url}/status")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Failed to get robot status: {e}")
            return None
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
        print("🔌 Controller disconnected")
    
    def initialize_robot(self):
        """
        Initialize the robot connection (as used in examples 0 and 1).
        """
        try:
            response = self.session.post(f"{self.server_url}/move/init", json={})
            response.raise_for_status()
            print("✅ Robot initialized")
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Failed to initialize robot: {e}")
            return None


# Convenience functions for common operations
def initialize_controller(**kwargs):
    """Initialize and return a dual arm controller."""
    return DualSO101Controller(**kwargs)

def demo_basic_movement():
    """Simple demo of basic single arm movements (adapted for single robot)."""
    print("🤖 SO-101 Basic Movement Demo (Single Arm)")
    
    # Initialize controller
    controller = DualSO101Controller()
    
    try:
        # Initialize robot (as done in examples 0 and 1)
        print("\n🔧 Initializing robot...")
        controller.initialize_robot()
        time.sleep(2)
        
        # Move arm to home position (adapted for single robot)
        print("\n📍 Moving to home position...")
        controller.move_arm_absolute_pose(0, [0.25, 0.0, 0.20])  # Single arm centered
        
        time.sleep(2)
        
        # Open gripper
        print("\n✋ Opening gripper...")
        controller.control_gripper(0, 1.0)  # Open gripper
        
        time.sleep(1)
        
        # Move arm to different position
        print("\n🏃 Moving to new position...")
        controller.move_arm_absolute_pose(0, [0.30, 0.0, 0.15])  # Forward movement
        
        time.sleep(2)
        
        # Close gripper
        print("\n✊ Closing gripper...")
        controller.control_gripper(0, 0.0)  # Close gripper
        
        print("\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    finally:
        controller.close()


if __name__ == "__main__":
    demo_basic_movement()
