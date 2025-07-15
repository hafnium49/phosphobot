#!/usr/bin/env python3
"""
🎯 Sequential Arm Movement Test
===============================

This test moves arms one at a time with clear delays to visually verify 
that both arms are actually moving independently.
"""

import time
from dual_so101_controller import DualSO101Controller


def sequential_test():
    print("🎯 SEQUENTIAL ARM MOVEMENT TEST")
    print("=" * 40)
    print("Watch carefully - each arm should move separately!")
    print()
    
    controller = DualSO101Controller()
    controller.initialize_robot()
    
    # Starting positions
    print("🏠 Moving both arms to starting positions...")
    controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20], [0, 0, 0])
    controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20], [0, 0, 0])
    time.sleep(2)
    
    print("\n" + "="*50)
    print("🎬 STARTING SEQUENTIAL MOVEMENTS")
    print("="*50)
    
    # Test 1: Left arm only
    print("\n👈 ONLY LEFT ARM (ID=0) SHOULD MOVE NOW!")
    print("Moving left arm to different position...")
    for i in range(3):
        print(f"  Left arm movement {i+1}/3...")
        controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25 + i*0.02], [0, 0, 0])
        time.sleep(1.5)
    
    time.sleep(2)
    
    # Test 2: Right arm only
    print("\n👉 ONLY RIGHT ARM (ID=1) SHOULD MOVE NOW!")
    print("Moving right arm to different position...")
    for i in range(3):
        print(f"  Right arm movement {i+1}/3...")
        controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25 + i*0.02], [0, 0, 0])
        time.sleep(1.5)
    
    time.sleep(2)
    
    # Test 3: Alternating
    print("\n🔄 ALTERNATING ARM MOVEMENTS")
    print("Arms should move one after the other...")
    for i in range(3):
        print(f"  Round {i+1}: Left arm...")
        controller.move_arm_absolute_pose(0, [0.20 + i*0.02, 0.15, 0.20], [0, 0, 0])
        time.sleep(1)
        
        print(f"  Round {i+1}: Right arm...")
        controller.move_arm_absolute_pose(1, [0.20 + i*0.02, -0.15, 0.20], [0, 0, 0])
        time.sleep(1)
    
    # Return to safe positions
    print("\n🏠 Returning to safe positions...")
    controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25], [0, 0, 0])
    controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25], [0, 0, 0])
    
    print("\n" + "="*50)
    print("✅ SEQUENTIAL TEST COMPLETE!")
    print("="*50)
    print("🔍 Did you observe:")
    print("   • Left arm moving alone during left-only phase?")
    print("   • Right arm moving alone during right-only phase?")
    print("   • Arms alternating during alternating phase?")
    print()
    print("If YES to all - the robot_id fix is working! 🎉")
    print("If NO to any - there may still be an issue. 🔧")


if __name__ == "__main__":
    sequential_test()
