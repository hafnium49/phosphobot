#!/usr/bin/env python3
"""
Basic SO-101 Arm Control Example (Dual & Single Robot Support)

This script demonstrates basic pose control for SO-101 robotic arms.
It supports both single robot and dual robot configurations.
Run with --single flag for single robot mode.
"""

import sys
import time
from dual_so101_controller import DualSO101Controller


def single_robot_demo(controller):
    """Demo for single robot setup."""
    print("🤖 SO-101 Basic Control Example (Single Robot Mode)")
    print("=================================================")
    
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
    
    print("\n✅ Single robot demonstration completed successfully!")


def dual_robot_demo(controller):
    """Demo for dual robot setup."""
    print("🤖 Dual SO-101 Basic Control Example")
    print("===================================")
    
    # Note: This example assumes two robots are available
    print("\n⚠️  DUAL ROBOT REQUIRED: This example needs two SO-101 robots")
    print("   If you only have one robot, use --single flag")
    
    # Check robot status (may not work if /status endpoint unavailable)
    print("\n📊 Checking robot status...")
    status = controller.get_robot_status()
    if status:
        print(f"Server status: {status}")
    else:
        print("⚠️ Robot status unavailable (endpoint may not exist)")
    
    print("\n🎯 Moving arms to initial positions...")
    
    # Move left arm (robot_id=0) to left side
    print("Moving left arm to left position...")
    controller.move_arm_absolute_pose(
        robot_id=0,
        position=[0.25, 0.15, 0.15],  # 25cm forward, 15cm left, 15cm up
        orientation=[0, 0, 0]  # No rotation
    )
    
    # Move right arm (robot_id=1) to right side
    print("Moving right arm to right position...")
    controller.move_arm_absolute_pose(
        robot_id=1,
        position=[0.25, -0.15, 0.15],  # 25cm forward, 15cm right, 15cm up
        orientation=[0, 0, 0]  # No rotation
    )
    
    time.sleep(3)
    
    print("\n🤏 Testing gripper control on both arms...")
    
    # Open both grippers
    print("Opening both grippers...")
    controller.control_gripper(robot_id=0, gripper_value=1.0)
    controller.control_gripper(robot_id=1, gripper_value=1.0)
    
    time.sleep(1)
    
    # Close both grippers
    print("Closing both grippers...")
    controller.control_gripper(robot_id=0, gripper_value=0.0)
    controller.control_gripper(robot_id=1, gripper_value=0.0)
    
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
    
    print("\n🎪 Testing coordinated movements...")
    
    # Test coordinated positions
    movements = [
        ([0.30, 0.15, 0.18], [0.30, -0.15, 0.18], "Forward positions"),
        ([0.20, 0.15, 0.22], [0.20, -0.15, 0.22], "High positions"),
        ([0.25, 0.10, 0.15], [0.25, -0.10, 0.15], "Close positions"),
        ([0.25, 0.15, 0.15], [0.25, -0.15, 0.15], "Home positions")
    ]
    
    for left_pos, right_pos, description in movements:
        print(f"Moving to {description}...")
        controller.move_arm_absolute_pose(
            robot_id=0,
            position=left_pos,
            orientation=[0, 0, 0]
        )
        controller.move_arm_absolute_pose(
            robot_id=1,
            position=right_pos,
            orientation=[0, 0, 0]
        )
        time.sleep(2)
    
    print("\n✅ Dual robot demonstration completed successfully!")
    print("💡 Try the other examples for more advanced functionality:")
    print("   - dual_arm_coordination.py: Synchronized movements")  
    print("   - interactive_control.py: Manual control interface")
    print("   - test_legacy_dual_robot.py: Legacy API tests")
    print("💡 Note: Dual robot examples require two connected SO-101 robots")
    print("💡 Use --single flag for single robot mode")
        

def main():
    # Check for single robot mode
    single_mode = "--single" in sys.argv or "-s" in sys.argv
    
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
        
        # Run appropriate demo based on mode
        if single_mode:
            single_robot_demo(controller)
        else:
            dual_robot_demo(controller)
            
    except Exception as e:
        print(f"❌ Error during execution: {e}")
    
    finally:
        # Clean up
        controller.close()
        print("\n👋 Controller closed. Goodbye!")
