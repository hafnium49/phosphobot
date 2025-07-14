#!/usr/bin/env python3
"""
Basic Dual SO-101 Arm Control Example

This script demonstrates basic pose control for two SO-101 robotic arms.
It shows how to move arms to specific positions and orientations.
"""

import time
from dual_so101_controller import DualSO101Controller


def main():
    print("🤖 Dual SO-101 Basic Control Example")
    print("===================================")
    
    # Initialize controller
    try:
        controller = DualSO101Controller()
    except Exception as e:
        print(f"❌ Failed to initialize controller: {e}")
        print("💡 Make sure phosphobot server is running: phosphobot run")
        return
    
    try:
        # Initialize robot connection
        print("\n🔧 Initializing robot connection...")
        result = controller.initialize_robot()
        if result:
            print(f"✅ Robot initialized: {result}")
        else:
            print("❌ Robot initialization failed")
            return
        
        time.sleep(1)
        
        # Note: This example assumes two robots are available
        print("\n⚠️  DUAL ROBOT REQUIRED: This example needs two SO-101 robots")
        print("   If you only have one robot, use single_arm_basic.py instead")
        
        # Check robot status (may not work if /status endpoint unavailable)
        print("\n📊 Checking robot status...")
        status = controller.get_robot_status()
        if status:
            print(f"Server status: {status}")
        else:
            print("⚠️ Robot status unavailable (endpoint may not exist)")
        
        print("\n🎯 Moving arms to initial positions...")
        
        # Move first arm (robot_id=0) to a specific pose
        print("Moving left arm (ID=0)...")
        try:
            controller.move_arm_absolute_pose(
                robot_id=0,
                position=[0.25, 0.15, 0.15],  # 25cm forward, 15cm right, 15cm up
                orientation=[0, 0, 0]  # No rotation
            )
        except Exception as e:
            print(f"❌ Failed to move arm 0: {e}")
        
        # Move second arm (robot_id=1) to a different pose
        print("Moving right arm (ID=1)...")
        try:
            controller.move_arm_absolute_pose(
                robot_id=1, 
                position=[0.25, -0.15, 0.15],  # 25cm forward, 15cm left, 15cm up
                orientation=[0, 0, 0]  # No rotation
            )
        except Exception as e:
            print(f"❌ Failed to move arm 1: {e}")
            print("💡 This may fail if only one robot is connected")
        
        time.sleep(2)
        
        print("\n🤏 Testing gripper control...")
        
        # Open both grippers
        print("Opening grippers...")
        try:
            controller.control_gripper(robot_id=0, gripper_value=1.0)
            controller.control_gripper(robot_id=1, gripper_value=1.0)
        except Exception as e:
            print(f"❌ Gripper control failed: {e}")
        
        time.sleep(1)
        
        # Close both grippers
        print("Closing grippers...")
        try:
            controller.control_gripper(robot_id=0, gripper_value=0.0)
            controller.control_gripper(robot_id=1, gripper_value=0.0)
        except Exception as e:
            print(f"❌ Gripper control failed: {e}")
        
        time.sleep(1)
        
        print("\n📐 Testing relative movements...")
        
        # Move both arms down by 5cm
        print("Moving both arms down by 5cm...")
        try:
            controller.move_arm_relative_pose(
                robot_id=0,
                delta_position=[0, 0, -5],  # Move 5cm down
            )
            
            controller.move_arm_relative_pose(
                robot_id=1,
                delta_position=[0, 0, -5],  # Move 5cm down
            )
        except Exception as e:
            print(f"❌ Relative movement failed: {e}")
        
        time.sleep(2)
        
        # Move arms back up
        print("Moving both arms back up...")
        try:
            controller.move_arm_relative_pose(
                robot_id=0,
                delta_position=[0, 0, 5],  # Move 5cm up
            )
            
            controller.move_arm_relative_pose(
                robot_id=1,
                delta_position=[0, 0, 5],  # Move 5cm up
            )
        except Exception as e:
            print(f"❌ Relative movement failed: {e}")
        
        print("\n✅ Basic control demonstration completed successfully!")
        print("💡 Try the other examples for more advanced functionality:")
        print("   - dual_arm_coordination.py: Synchronized movements")  
        print("   - interactive_control.py: Manual control interface")
        print("   - single_arm_basic.py: Single robot version")
        print("   - single_arm_test_clean.py: Simple tests")
        print("💡 Note: Dual robot examples require two connected SO-101 robots")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
    
    finally:
        # Clean up
        controller.close()
        print("\n👋 Controller closed. Goodbye!")


if __name__ == "__main__":
    main()
