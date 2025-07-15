#!/usr/bin/env python3
"""
🔧 Robot ID Fix Test
===================

Test to verify both arms move correctly after adding robot_id to API calls.
"""

import time
from dual_so101_controller import DualSO101Controller


def test_both_arms():
    print("🔧 TESTING ROBOT ID FIX")
    print("=" * 30)
    
    controller = DualSO101Controller()
    controller.initialize_robot()
    
    print("\n🧪 Test 1: Move Left Arm (ID=0) Only")
    print("Moving left arm to [0.25, 0.15, 0.20]...")
    controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20], [0, 0, 0])
    time.sleep(2)
    
    print("\n🧪 Test 2: Move Right Arm (ID=1) Only")
    print("Moving right arm to [0.25, -0.15, 0.20]...")
    controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20], [0, 0, 0])
    time.sleep(2)
    
    print("\n🧪 Test 3: Move Left Arm Higher")
    print("Moving left arm up to [0.25, 0.15, 0.25]...")
    controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25], [0, 0, 0])
    time.sleep(2)
    
    print("\n🧪 Test 4: Move Right Arm Higher")
    print("Moving right arm up to [0.25, -0.15, 0.25]...")
    controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25], [0, 0, 0])
    time.sleep(2)
    
    print("\n🧪 Test 5: Gripper Test")
    print("Opening left gripper (ID=0)...")
    controller.control_gripper(0, 1.0)
    time.sleep(1)
    
    print("Opening right gripper (ID=1)...")
    controller.control_gripper(1, 1.0)
    time.sleep(1)
    
    print("\n✅ BOTH ARMS SHOULD HAVE MOVED!")
    print("If only one arm moved, there's still an issue.")
    print("If both arms moved, the fix is working!")


if __name__ == "__main__":
    test_both_arms()
