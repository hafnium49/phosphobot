#!/usr/bin/env python3
"""
SO-101 Inverse Kinematics Examples

This script demonstrates how to use the built-in inverse kinematics functionality
in the phosphobot API for precise end effector control.
"""

import time
import numpy as np
from dual_so101_controller import DualSO101Controller


class InverseKinematicsDemo:
    """Demonstrates inverse kinematics functionality in phosphobot."""
    
    def __init__(self, controller: DualSO101Controller):
        self.controller = controller
    
    def demonstrate_ik_basics(self):
        """Show basic inverse kinematics functionality."""
        print("\n🧮 Inverse Kinematics Basics")
        print("=" * 30)
        
        # The IK is automatically called when you use move_arm_absolute_pose
        print("1. When you call move_arm_absolute_pose():")
        print("   - You specify: end effector position + orientation")
        print("   - Robot calculates: joint angles using inverse kinematics")
        print("   - Robot moves: all joints to achieve desired pose")
        
        print("\n📐 Example IK calculation:")
        target_position = [0.25, 0.15, 0.20]
        target_orientation = [0, 45, -15]
        
        print(f"   Target position: {target_position} (meters)")
        print(f"   Target orientation: {target_orientation} (degrees)")
        
        # This internally calls inverse_kinematics() to calculate joint angles
        self.controller.move_arm_absolute_pose(
            robot_id=0,
            position=target_position,
            orientation=target_orientation
        )
        
        print("   ✅ Robot automatically calculated and moved to joint angles!")
        time.sleep(2)
    
    def demonstrate_forward_kinematics(self):
        """Show forward kinematics functionality."""
        print("\n🔄 Forward Kinematics (Current Pose)")
        print("=" * 35)
        
        print("Forward kinematics tells us the current end effector pose")
        print("based on the current joint angles.")
        
        try:
            # Get current pose using forward kinematics
            current_pose = self.controller.get_current_pose(robot_id=0)
            print(f"\n📍 Current end effector pose:")
            print(f"   Position: {current_pose}")
            
            # Note: The controller wraps the forward_kinematics() method
            # which internally uses the robot's forward kinematics calculation
            
        except Exception as e:
            print(f"⚠️ Could not get current pose: {e}")
        
        time.sleep(1)
    
    def demonstrate_ik_vs_joint_control(self):
        """Compare IK-based control vs direct joint control."""
        print("\n⚖️ IK Control vs Joint Control")
        print("=" * 30)
        
        print("Method 1: End Effector Control (using IK) - EASY ✅")
        print("   You think: 'Move gripper to this position'")
        
        # Easy approach - specify where you want the gripper
        target_pos = [0.22, 0.12, 0.18]
        print(f"   Command: Move to position {target_pos}")
        
        self.controller.move_arm_absolute_pose(
            robot_id=0,
            position=target_pos,
            orientation=[0, 30, 0]
        )
        print("   ✅ Robot automatically calculates joint angles with IK")
        time.sleep(2)
        
        print("\nMethod 2: Direct Joint Control - COMPLEX ❌")
        print("   You think: 'Set each joint to specific angles'")
        print("   Example joint angles: [30°, 45°, -60°, 90°, 15°]")
        print("   ❌ Hard to visualize final gripper position!")
        print("   ❌ Must manually calculate angles for desired pose!")
        print("   ❌ Complex math and trial-and-error required!")
        
        print("\n💡 Conclusion: IK-based control is much more intuitive!")
    
    def demonstrate_ik_precision(self):
        """Show IK precision and error handling."""
        print("\n🎯 IK Precision and Limits")
        print("=" * 25)
        
        print("Testing IK precision with challenging poses...")
        
        # Test 1: Reachable pose
        print("\n1. Testing reachable pose:")
        reachable_pos = [0.20, 0.10, 0.15]
        try:
            self.controller.move_arm_absolute_pose(
                robot_id=0,
                position=reachable_pos,
                orientation=[0, 0, 0],
                position_tolerance=0.005,  # 5mm precision
                max_trials=3
            )
            print(f"   ✅ Successfully reached {reachable_pos} with 5mm precision")
        except Exception as e:
            print(f"   ❌ Failed to reach pose: {e}")
        
        time.sleep(1)
        
        # Test 2: Edge of workspace
        print("\n2. Testing workspace limits:")
        edge_pos = [0.35, 0.20, 0.10]  # Near workspace edge
        try:
            self.controller.move_arm_absolute_pose(
                robot_id=0,
                position=edge_pos,
                orientation=[0, 60, 0],  # Steep downward angle
                max_trials=5
            )
            print(f"   ✅ Reached edge position {edge_pos}")
        except Exception as e:
            print(f"   ⚠️ Edge position challenging: {e}")
        
        time.sleep(1)
        
        # Test 3: Impossible pose (outside workspace)
        print("\n3. Testing impossible pose:")
        impossible_pos = [0.50, 0.30, 0.05]  # Outside workspace
        try:
            self.controller.move_arm_absolute_pose(
                robot_id=0,
                position=impossible_pos,
                orientation=[0, 0, 0],
                max_trials=1
            )
            print(f"   ❓ Unexpectedly reached {impossible_pos}")
        except Exception as e:
            print(f"   ✅ Correctly failed for impossible pose: {e}")
    
    def demonstrate_ik_alternatives(self):
        """Show different IK solutions for same end effector pose."""
        print("\n🔄 Multiple IK Solutions")
        print("=" * 25)
        
        print("Same end effector pose can have multiple joint configurations:")
        
        target_position = [0.25, 0.15, 0.18]
        orientations = [
            [0, 0, 0],      # Gripper horizontal
            [0, 30, 0],     # Tilted down 30°
            [0, 0, 45],     # Rotated 45°
        ]
        
        for i, orientation in enumerate(orientations, 1):
            print(f"\n{i}. Moving to position {target_position}")
            print(f"   with orientation {orientation}")
            
            self.controller.move_arm_absolute_pose(
                robot_id=0,
                position=target_position,
                orientation=orientation
            )
            
            print("   ✅ Same position, different orientation = different joint angles")
            time.sleep(2)
    
    def practical_ik_tips(self):
        """Provide practical tips for using IK effectively."""
        print("\n💡 Practical IK Tips")
        print("=" * 20)
        
        tips = [
            "1. Start with simple orientations [0,0,0] for initial positioning",
            "2. Use position_tolerance and orientation_tolerance for precision control",
            "3. Increase max_trials for challenging poses",
            "4. Test workspace limits gradually - don't jump to extremes",
            "5. Use relative movements for fine adjustments",
            "6. IK automatically handles collision avoidance within joint limits",
            "7. Forward kinematics helps verify your poses are correct"
        ]
        
        for tip in tips:
            print(f"   {tip}")
            time.sleep(0.5)


def main():
    print("🤖 SO-101 Inverse Kinematics Demo")
    print("=================================")
    
    # Initialize controller
    try:
        controller = DualSO101Controller()
        ik_demo = InverseKinematicsDemo(controller)
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    try:
        # Move to safe starting position
        print("🔧 Moving to safe starting position...")
        controller.move_arm_absolute_pose(
            robot_id=0,
            position=[0.25, 0.15, 0.25],
            orientation=[0, 0, 0]
        )
        time.sleep(2)
        
        # Run demonstrations
        ik_demo.demonstrate_ik_basics()
        ik_demo.demonstrate_forward_kinematics()
        ik_demo.demonstrate_ik_vs_joint_control()
        ik_demo.demonstrate_ik_precision()
        ik_demo.demonstrate_ik_alternatives()
        ik_demo.practical_ik_tips()
        
        print("\n✅ Inverse Kinematics demonstration completed!")
        print("\n🎓 Key Takeaways:")
        print("   • IK is automatically used in move_arm_absolute_pose()")
        print("   • You specify end effector pose, robot calculates joint angles")
        print("   • Much more intuitive than manual joint control")
        print("   • Built-in precision control and error handling")
        print("   • Forward kinematics verifies current poses")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
    
    finally:
        controller.close()
        print("\n👋 IK demo finished!")


if __name__ == "__main__":
    main()
