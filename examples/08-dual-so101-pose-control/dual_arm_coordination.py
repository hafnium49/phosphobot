#!/usr/bin/env python3
"""
Dual SO-101 Arm Coordination Example

This script demonstrates synchronized dual-arm movements and coordination
patterns for collaborative tasks.
"""

import time
import threading
import numpy as np
from dual_so101_controller import DualSO101Controller


class DualArmCoordinator:
    """Coordinator for synchronized dual-arm movements."""
    
    # Common end effector pose presets (position in meters, orientation in degrees)
    # These define where the gripper/tool tip should be positioned and oriented
    POSES = {
        'safe_left': {'position': [0.25, 0.15, 0.25], 'orientation': [0, 0, 0]},
        'safe_right': {'position': [0.25, -0.15, 0.25], 'orientation': [0, 0, 0]},
        'home_left': {'position': [0.20, 0.10, 0.18], 'orientation': [0, 0, -15]},
        'home_right': {'position': [0.20, -0.10, 0.18], 'orientation': [0, 0, 15]},
        'pickup_left': {'position': [0.30, 0.12, 0.12], 'orientation': [0, 45, 0]},
        'pickup_right': {'position': [0.30, -0.12, 0.12], 'orientation': [0, 45, 0]},
        'handoff_left': {'position': [0.20, 0.05, 0.18], 'orientation': [0, 0, 45]},
        'handoff_right': {'position': [0.20, -0.05, 0.18], 'orientation': [0, 0, -45]},
    }
    
    def __init__(self, controller: DualSO101Controller):
        self.controller = controller
    
    def synchronized_movement(self, 
                            left_pose: list[float], 
                            right_pose: list[float],
                            left_orientation: list[float] = None,
                            right_orientation: list[float] = None):
        """
        Move both arm end effectors simultaneously to specified poses.
        
        This method uses INVERSE KINEMATICS automatically:
        1. You specify WHERE you want each gripper (position + orientation)
        2. Robot calculates WHAT joint angles are needed (inverse kinematics)
        3. Both arms move to achieve the desired end effector poses
        
        Args:
            left_pose: [x, y, z] position of left arm's end effector in meters
            right_pose: [x, y, z] position of right arm's end effector in meters  
            left_orientation: [rx, ry, rz] orientation of left end effector in degrees
            right_orientation: [rx, ry, rz] orientation of right end effector in degrees
            
        Note: The pose refers to the gripper/tool tip position and orientation,
              not the individual joint angles. IK is performed automatically.
        """
        
        def move_left():
            self.controller.move_arm_absolute_pose(
                robot_id=0, 
                position=left_pose,
                orientation=left_orientation
            )
        
        def move_right():
            self.controller.move_arm_absolute_pose(
                robot_id=1,
                position=right_pose,
                orientation=right_orientation
            )
        
        # Start movements in parallel
        left_thread = threading.Thread(target=move_left)
        right_thread = threading.Thread(target=move_right)
        
        print(f"🤝 Synchronizing movement: Left→{left_pose}, Right→{right_pose}")
        
        left_thread.start()
        right_thread.start()
        
        # Wait for both to complete
        left_thread.join()
        right_thread.join()
        
        print("✅ Synchronized movement completed!")
    
    def mirror_movement(self, center_pose: list[float], offset: float = 0.15):
        """Move arms to mirror positions around a center point."""
        left_pose = [center_pose[0], center_pose[1] + offset, center_pose[2]]
        right_pose = [center_pose[0], center_pose[1] - offset, center_pose[2]]
        
        # Mirror orientations (rotate wrists inward)
        left_orientation = [0, 0, -15]  # Rotate left wrist inward
        right_orientation = [0, 0, 15]   # Rotate right wrist inward
        
        self.synchronized_movement(
            left_pose, right_pose, 
            left_orientation, right_orientation
        )
    
    def collaborative_pick_place(self):
        """Demonstrate a collaborative pick-and-place sequence."""
        print("\n🤝 Collaborative Pick-and-Place Sequence")
        print("=" * 40)
        
        # Phase 1: Approach positions
        print("Phase 1: Moving to approach positions...")
        self.synchronized_movement(
            left_pose=[0.3, 0.2, 0.25],   # Left approach
            right_pose=[0.3, -0.2, 0.25]  # Right approach
        )
        time.sleep(1)
        
        # Phase 2: Pre-grasp with grippers open
        print("Phase 2: Opening grippers and moving to pre-grasp...")
        self.controller.control_gripper(robot_id=0, gripper_value=1.0)
        self.controller.control_gripper(robot_id=1, gripper_value=1.0)
        
        self.synchronized_movement(
            left_pose=[0.25, 0.15, 0.15],   # Left pre-grasp
            right_pose=[0.25, -0.15, 0.15]  # Right pre-grasp
        )
        time.sleep(1)
        
        # Phase 3: Grasp objects
        print("Phase 3: Grasping objects...")
        self.synchronized_movement(
            left_pose=[0.25, 0.15, 0.12],   # Lower to grasp
            right_pose=[0.25, -0.15, 0.12]  # Lower to grasp
        )
        
        time.sleep(0.5)
        
        # Close grippers
        self.controller.control_gripper(robot_id=0, gripper_value=0.0)
        self.controller.control_gripper(robot_id=1, gripper_value=0.0)
        
        time.sleep(1)
        
        # Phase 4: Lift objects
        print("Phase 4: Lifting objects...")
        self.synchronized_movement(
            left_pose=[0.25, 0.15, 0.20],   # Lift up
            right_pose=[0.25, -0.15, 0.20]  # Lift up
        )
        time.sleep(1)
        
        # Phase 5: Transport to center (collaborative handoff position)
        print("Phase 5: Transporting to center for handoff...")
        self.synchronized_movement(
            left_pose=[0.20, 0.05, 0.18],   # Move toward center
            right_pose=[0.20, -0.05, 0.18]  # Move toward center
        )
        time.sleep(2)
        
        # Phase 6: Place objects at new locations
        print("Phase 6: Placing objects at new locations...")
        self.synchronized_movement(
            left_pose=[0.15, 0.25, 0.15],   # New left position
            right_pose=[0.15, -0.25, 0.15]  # New right position
        )
        time.sleep(1)
        
        # Release objects
        print("Phase 7: Releasing objects...")
        self.controller.control_gripper(robot_id=0, gripper_value=1.0)
        self.controller.control_gripper(robot_id=1, gripper_value=1.0)
        
        time.sleep(1)
        
        # Phase 8: Return to safe positions
        print("Phase 8: Returning to safe positions...")
        self.synchronized_movement(
            left_pose=[0.25, 0.15, 0.25],   # Safe left
            right_pose=[0.25, -0.15, 0.25]  # Safe right
        )
        
        print("✅ Collaborative sequence completed!")
    
    def figure_eight_pattern(self, duration: float = 10.0):
        """Move arms in a coordinated figure-eight pattern."""
        print(f"\n∞ Figure-Eight Pattern for {duration} seconds")
        print("=" * 35)
        
        start_time = time.time()
        center = [0.25, 0.0, 0.18]
        amplitude = 0.12
        
        while time.time() - start_time < duration:
            t = (time.time() - start_time) * 2  # Speed factor
            
            # Calculate figure-eight positions
            left_x = center[0] + amplitude * np.sin(t)
            left_y = center[1] + 0.15 + amplitude * np.sin(2*t) / 2
            left_z = center[2] + amplitude * np.cos(2*t) / 4
            
            right_x = center[0] + amplitude * np.sin(t + np.pi)  # 180° phase shift
            right_y = center[1] - 0.15 - amplitude * np.sin(2*t) / 2
            right_z = center[2] + amplitude * np.cos(2*t + np.pi) / 4
            
            # Move arms to calculated positions
            try:
                self.controller.move_arm_relative_pose(
                    robot_id=0,
                    delta_position=[
                        (left_x - center[0]) * 100,  # Convert to cm
                        (left_y - (center[1] + 0.15)) * 100,
                        (left_z - center[2]) * 100
                    ]
                )
                
                self.controller.move_arm_relative_pose(
                    robot_id=1,
                    delta_position=[
                        (right_x - center[0]) * 100,  # Convert to cm
                        (right_y - (center[1] - 0.15)) * 100,
                        (right_z - center[2]) * 100
                    ]
                )
                
                time.sleep(0.1)  # Small delay for smooth movement
                
            except Exception as e:
                print(f"⚠️ Movement adjustment failed: {e}")
                break
        
        print("✅ Figure-eight pattern completed!")
    
    def move_to_preset(self, robot_id: int, preset_name: str):
        """
        Move arm end effector to a predefined pose preset.
        
        Args:
            robot_id: 0 for left arm, 1 for right arm
            preset_name: Name of preset pose for the end effector
        """
        if preset_name not in self.POSES:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(self.POSES.keys())}")
        
        pose = self.POSES[preset_name]
        arm_name = "Left" if robot_id == 0 else "Right"
        
        self.controller.move_arm_absolute_pose(
            robot_id=robot_id,
            position=pose['position'],
            orientation=pose['orientation']
        )
        print(f"✅ {arm_name} arm moved to '{preset_name}' pose")
    
    def move_both_to_preset(self, left_preset: str, right_preset: str):
        """Move both arms to preset poses simultaneously."""
        left_pose = self.POSES[left_preset]
        right_pose = self.POSES[right_preset]
        
        self.synchronized_movement(
            left_pose=left_pose['position'],
            right_pose=right_pose['position'],
            left_orientation=left_pose['orientation'],
            right_orientation=right_pose['orientation']
        )
    
    def create_custom_pose(self, 
                          x: float, y: float, z: float,
                          rx: float = 0, ry: float = 0, rz: float = 0) -> dict:
        """
        Create a custom end effector pose dictionary.
        
        Args:
            x, y, z: End effector position coordinates in meters
            rx, ry, rz: End effector orientation (Euler angles) in degrees
            
        Returns:
            Dictionary with 'position' and 'orientation' keys for end effector pose
        """
        return {
            'position': [x, y, z],
            'orientation': [rx, ry, rz]
        }
    
    def demonstrate_poses(self):
        """Demonstrate different pose presets."""
        print("\n🎭 Pose Demonstration")
        print("=" * 20)
        
        poses_to_demo = [
            ('safe_left', 'safe_right'),
            ('home_left', 'home_right'), 
            ('pickup_left', 'pickup_right'),
            ('handoff_left', 'handoff_right')
        ]
        
        for left_preset, right_preset in poses_to_demo:
            print(f"\nMoving to: {left_preset} & {right_preset}")
            self.move_both_to_preset(left_preset, right_preset)
            time.sleep(2)


def main():
    print("🤖 Dual SO-101 Coordination Example")
    print("==================================")
    
    # Initialize controller
    try:
        controller = DualSO101Controller()
        coordinator = DualArmCoordinator(controller)
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    try:
        print("\n🎯 Starting coordination demonstrations...")
        
        # Demo 1: Basic synchronized movement
        print("\nDemo 1: Basic synchronized movement")
        coordinator.synchronized_movement(
            left_pose=[0.25, 0.15, 0.20],
            right_pose=[0.25, -0.15, 0.20]
        )
        time.sleep(2)
        
        # Demo 2: Mirror movement
        print("\nDemo 2: Mirror movement around center")
        coordinator.mirror_movement(center_pose=[0.25, 0.0, 0.18], offset=0.12)
        time.sleep(2)
        
        # Demo 3: Collaborative pick-and-place
        print("\nDemo 3: Collaborative pick-and-place")
        coordinator.collaborative_pick_place()
        time.sleep(2)
        
        # Demo 4: Pose presets demonstration
        print("\nDemo 4: Pose presets demonstration")
        coordinator.demonstrate_poses()
        time.sleep(2)
        
        # Demo 5: Custom poses
        print("\nDemo 5: Custom pose creation")
        custom_left = coordinator.create_custom_pose(x=0.22, y=0.08, z=0.16, rx=0, ry=30, rz=-20)
        custom_right = coordinator.create_custom_pose(x=0.22, y=-0.08, z=0.16, rx=0, ry=30, rz=20)
        
        coordinator.synchronized_movement(
            left_pose=custom_left['position'],
            right_pose=custom_right['position'],
            left_orientation=custom_left['orientation'],
            right_orientation=custom_right['orientation']
        )
        time.sleep(2)
        
        # Demo 6: Figure-eight pattern (uncomment to try)
        # print("\nDemo 6: Figure-eight coordination pattern")
        # coordinator.figure_eight_pattern(duration=5.0)
        
        print("\n✅ All coordination demonstrations completed!")
        print("💡 Explore related examples:")
        print("   - dual_arm_basic.py: Basic dual-arm control")
        print("   - interactive_control.py: Manual control interface")
        print("   - ../10-inverse-kinematics-demo/: Learn about inverse kinematics")
        print("   - ../09-workspace-analysis/: Workspace validation and analysis")
        
    except Exception as e:
        print(f"❌ Error during coordination: {e}")
    
    finally:
        controller.close()
        print("\n👋 Coordination demo finished!")


if __name__ == "__main__":
    main()
