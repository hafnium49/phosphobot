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
        # Check robot status
        print("\n📊 Checking robot status...")
        status = controller.get_robot_status()
        print(f"Server status: {status}")
        
        print("\n🎯 Moving arms to initial positions...")
        
        # Move first arm (robot_id=0) to a specific pose
        print("Moving left arm (ID=0)...")
        controller.move_arm_absolute_pose(
            robot_id=0,
            position=[0.25, 0.15, 0.15],  # 25cm forward, 15cm right, 15cm up
            orientation=[0, 0, 0]  # No rotation
        )
        
        # Move second arm (robot_id=1) to a different pose
        print("Moving right arm (ID=1)...")
        controller.move_arm_absolute_pose(
            robot_id=1, 
            position=[0.25, -0.15, 0.15],  # 25cm forward, 15cm left, 15cm up
            orientation=[0, 0, 0]  # No rotation
        )
        
        time.sleep(2)
        
        print("\n🤏 Testing gripper control...")
        
        # Open both grippers
        print("Opening grippers...")
        controller.control_gripper(robot_id=0, open_command=1.0)
        controller.control_gripper(robot_id=1, open_command=1.0)
        
        time.sleep(1)
        
        # Close both grippers
        print("Closing grippers...")
        controller.control_gripper(robot_id=0, open_command=0.0)
        controller.control_gripper(robot_id=1, open_command=0.0)
        
        time.sleep(1)
        
        print("\n📐 Testing relative movements...")
        
        # Move both arms down by 5cm
        print("Moving both arms down by 5cm...")
        controller.move_arm_relative_pose(
            robot_id=0,
            delta_position=[0, 0, -5],  # Move 5cm down
        )
        
        controller.move_arm_relative_pose(
            robot_id=1,
            delta_position=[0, 0, -5],  # Move 5cm down
        )
        
        time.sleep(2)
        
        # Move arms back up
        print("Moving both arms back up...")
        controller.move_arm_relative_pose(
            robot_id=0,
            delta_position=[0, 0, 5],  # Move 5cm up
        )
        
        controller.move_arm_relative_pose(
            robot_id=1,
            delta_position=[0, 0, 5],  # Move 5cm up
        )
        
        print("\n✅ Basic control demonstration completed successfully!")
        print("💡 Try the other examples for more advanced functionality:")
        print("   - dual_arm_coordination.py: Synchronized movements")
        print("   - interactive_control.py: Manual control interface")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
    
    finally:
        # Clean up
        controller.close()
        print("\n👋 Controller closed. Goodbye!")


if __name__ == "__main__":
    main()
