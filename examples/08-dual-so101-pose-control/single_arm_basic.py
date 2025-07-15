#!/usr/bin/env python3
"""
Basic SO-101 Arm Control Example (Single Robot Version)

This script demonstrates basic pose control for a single SO-101 robotic arm.
It shows how to move the arm to specific positions and orientations.

CORRECTED VERSION: Adapted from dual_arm_basic.py to work with single robot setup.
"""

import time
from dual_so101_controller import DualSO101Controller


def main():
    print("🤖 SO-101 Basic Control Example (Single Robot)")
    print("==============================================")
    
    # Initialize controller
    try:
        controller = DualSO101Controller()
    except Exception as e:
        print(f"❌ Failed to initialize controller: {e}")
        print("💡 Make sure phosphobot server is running: phosphobot run")
        return
    
    try:
        # Initialize robot
        print("\n🔧 Initializing robot...")
        result = controller.initialize_robot()
        if result:
            print(f"✅ Robot initialized: {result}")
        else:
            print("❌ Robot initialization failed")
            return
        
        time.sleep(1)
        
        print("\n🎯 Moving arm to initial position...")
        
        # Move arm (robot_id=0) to a specific pose
        print("Moving arm to center position...")
        controller.move_arm_absolute_pose(
            robot_id=0,
            position=[0.25, 0.0, 0.15],  # 25cm forward, centered, 15cm up
            orientation=[0, 0, 0]  # No rotation
        )
        
        time.sleep(2)
        
        print("\n🤏 Testing gripper control...")
        
        # Open gripper
        print("Opening gripper...")
        controller.control_gripper(robot_id=0, gripper_value=1.0)
        
        time.sleep(1)
        
        # Close gripper
        print("Closing gripper...")
        controller.control_gripper(robot_id=0, gripper_value=0.0)
        
        time.sleep(1)
        
        print("\n📐 Testing relative movements...")
        
        # Move arm down by 5cm
        print("Moving arm down by 5cm...")
        controller.move_arm_relative_pose(
            robot_id=0,
            delta_position=[0, 0, -5],  # Move 5cm down
        )
        
        time.sleep(2)
        
        # Move arm back up
        print("Moving arm back up...")
        controller.move_arm_relative_pose(
            robot_id=0,
            delta_position=[0, 0, 5],  # Move 5cm up
        )
        
        time.sleep(1)
        
        # Test different positions
        print("\n🎪 Testing various positions...")
        
        positions = [
            ([0.30, 0.10, 0.18], "Forward-right position"),
            ([0.30, -0.10, 0.18], "Forward-left position"), 
            ([0.20, 0.0, 0.22], "Center-high position"),
            ([0.25, 0.0, 0.15], "Home position")
        ]
        
        for position, description in positions:
            print(f"Moving to {description}...")
            controller.move_arm_absolute_pose(
                robot_id=0,
                position=position,
                orientation=[0, 0, 0]
            )
            time.sleep(1.5)
        
        print("\n✅ Basic control demonstration completed successfully!")
        print("💡 Try the other corrected examples:")
        print("   - single_arm_test_clean.py: Simple test movements")
        print("   - interactive_control_single.py: Manual control interface") 
        print("   - Or explore the original dual-arm examples when you have two robots")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        controller.close()
        print("\n👋 Controller closed. Goodbye!")


if __name__ == "__main__":
    main()
