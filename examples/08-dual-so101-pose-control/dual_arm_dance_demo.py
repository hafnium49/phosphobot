#!/usr/bin/env python3
"""
🤖 DUAL ARM DANCE DEMO - Example 8 Finale
========================================

This demonstrates coordinated dual-arm movement patterns with two SO-101 robots.
A choreographed sequence showcasing the full capabilities of the dual-arm system.
"""

import time
import sys
from dual_so101_controller import DualSO101Controller


def dance_sequence_1(controller):
    """Wave motion with both arms."""
    print("🎭 Sequence 1: Synchronized Wave Dance")
    
    # Starting positions
    controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20], [0, 0, 0])
    controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20], [0, 0, 0])
    time.sleep(0.5)
    
    # Wave motion
    for i in range(3):
        print(f"  Wave {i+1}/3...")
        # Up
        controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25], [0, 0, 0])
        controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25], [0, 0, 0])
        time.sleep(0.3)
        
        # Down
        controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.15], [0, 0, 0])
        controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.15], [0, 0, 0])
        time.sleep(0.3)
    
    print("✅ Wave dance completed!")


def dance_sequence_2(controller):
    """Alternating arm movements."""
    print("🎭 Sequence 2: Alternating Arm Dance")
    
    positions = [
        ([0.25, 0.15, 0.25], [0.25, -0.15, 0.15]),  # Left up, right down
        ([0.25, 0.15, 0.15], [0.25, -0.15, 0.25]),  # Left down, right up
        ([0.25, 0.20, 0.20], [0.25, -0.20, 0.20]),  # Both out
        ([0.25, 0.10, 0.20], [0.25, -0.10, 0.20]),  # Both in
    ]
    
    for i, (left_pos, right_pos) in enumerate(positions):
        print(f"  Move {i+1}/4...")
        controller.move_arm_absolute_pose(0, left_pos, [0, 0, 0])
        controller.move_arm_absolute_pose(1, right_pos, [0, 0, 0])
        time.sleep(0.5)
    
    print("✅ Alternating dance completed!")


def dance_sequence_3(controller):
    """Gripper choreography."""
    print("🎭 Sequence 3: Gripper Choreography")
    
    # Open and close in sequence
    patterns = [
        (1.0, 0.0),  # Left open, right closed
        (0.0, 1.0),  # Left closed, right open  
        (1.0, 1.0),  # Both open
        (0.0, 0.0),  # Both closed
    ]
    
    for i, (left_gripper, right_gripper) in enumerate(patterns):
        print(f"  Gripper pattern {i+1}/4...")
        controller.control_gripper(0, left_gripper)
        controller.control_gripper(1, right_gripper)
        time.sleep(0.5)
    
    print("✅ Gripper choreography completed!")


def main():
    print("🎪 DUAL ARM DANCE DEMONSTRATION")
    print("=" * 50)
    print("🤖 Choreographed movements with two SO-101 robots")
    print()
    
    # Initialize
    try:
        controller = DualSO101Controller()
        controller.initialize_robot()
        print("✅ Dual arm system ready!")
        print()
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    # Move to starting positions
    print("🎬 Setting up starting positions...")
    controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20], [0, 0, 0])
    controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20], [0, 0, 0])
    controller.control_gripper(0, 1.0)  # Open
    controller.control_gripper(1, 1.0)  # Open
    time.sleep(1)
    
    print("🎵 Starting choreographed sequence...")
    print()
    
    # Perform dance sequences
    try:
        dance_sequence_1(controller)
        time.sleep(1)
        
        dance_sequence_2(controller)
        time.sleep(1)
        
        dance_sequence_3(controller)
        time.sleep(1)
        
    except Exception as e:
        print(f"⚠️ Dance sequence error: {e}")
    
    # Finale
    print("\n🎆 GRAND FINALE")
    try:
        print("Moving to finale positions...")
        controller.move_arm_absolute_pose(0, [0.20, 0.20, 0.25], [0, 0, 0])
        controller.move_arm_absolute_pose(1, [0.20, -0.20, 0.25], [0, 0, 0])
        time.sleep(0.5)
        
        print("Final gripper flourish...")
        for _ in range(3):
            controller.control_gripper(0, 1.0)
            controller.control_gripper(1, 1.0)
            time.sleep(0.2)
            controller.control_gripper(0, 0.0)
            controller.control_gripper(1, 0.0)
            time.sleep(0.2)
        
        print("Returning to safe positions...")
        controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25], [0, 0, 0])
        controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25], [0, 0, 0])
        controller.control_gripper(0, 1.0)
        controller.control_gripper(1, 1.0)
        
        print("✅ Finale completed!")
        
    except Exception as e:
        print(f"⚠️ Finale error: {e}")
    
    print()
    print("🎉 DUAL ARM DANCE COMPLETE!")
    print("=" * 50)
    print("🤖 Both robots performed flawlessly!")
    print("✨ Example 8 dual-arm capabilities fully demonstrated")
    print()
    print("🚀 Your dual SO-101 system is ready for:")
    print("   • Complex assembly operations")
    print("   • Collaborative manipulation tasks") 
    print("   • Synchronized pick-and-place")
    print("   • Advanced robotics research")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Dance interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
