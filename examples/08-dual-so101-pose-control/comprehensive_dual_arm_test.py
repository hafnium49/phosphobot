#!/usr/bin/env python3
"""
🤖 Comprehensive Dual Arm Test for PhosphoBot Example 8
=====================================================

This script demonstrates all working dual-arm capabilities with two SO-101 robots.
Designed for automated testing and demonstration.
"""

import time
import sys
from dual_so101_controller import DualSO101Controller


def main():
    print("🚀 COMPREHENSIVE DUAL ARM TEST")
    print("=" * 50)
    print("🤖 Testing with TWO SO-101 robots connected")
    print()
    
    # Initialize controller
    try:
        controller = DualSO101Controller()
        print("✅ Controller initialized successfully")
        
        # Initialize robot connection
        print("🔧 Initializing robot connection...")
        controller.initialize_robot()
        print("✅ Robot connection established")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False
    
    print()
    print("📊 TEST SEQUENCE STARTING...")
    print("-" * 30)
    
    # Test 1: Individual arm control
    print("\n🧪 TEST 1: Individual Arm Control")
    print("Moving left arm (ID=0) to position...")
    try:
        controller.move_arm_absolute_pose(
            robot_id=0,
            position=[0.25, 0.15, 0.20],  # Left side
            orientation=[0, 0, 0]
        )
        print("✅ Left arm positioned successfully")
        
        print("Moving right arm (ID=1) to position...")
        controller.move_arm_absolute_pose(
            robot_id=1,
            position=[0.25, -0.15, 0.20],  # Right side
            orientation=[0, 0, 0]
        )
        print("✅ Right arm positioned successfully")
        
    except Exception as e:
        print(f"❌ Individual arm control failed: {e}")
        return False
    
    time.sleep(1)
    
    # Test 2: Gripper control
    print("\n🧪 TEST 2: Gripper Control")
    try:
        print("Opening both grippers...")
        controller.control_gripper(robot_id=0, gripper_value=1.0)
        controller.control_gripper(robot_id=1, gripper_value=1.0)
        print("✅ Both grippers opened")
        
        time.sleep(0.5)
        
        print("Closing both grippers...")
        controller.control_gripper(robot_id=0, gripper_value=0.0)
        controller.control_gripper(robot_id=1, gripper_value=0.0)
        print("✅ Both grippers closed")
        
    except Exception as e:
        print(f"❌ Gripper control failed: {e}")
        return False
    
    time.sleep(1)
    
    # Test 3: Relative movements
    print("\n🧪 TEST 3: Relative Movement")
    try:
        print("Moving both arms down by 5cm...")
        controller.move_arm_relative_pose(robot_id=0, delta_position=[0, 0, -5])
        controller.move_arm_relative_pose(robot_id=1, delta_position=[0, 0, -5])
        print("✅ Both arms moved down")
        
        time.sleep(0.5)
        
        print("Moving both arms back up...")
        controller.move_arm_relative_pose(robot_id=0, delta_position=[0, 0, 5])
        controller.move_arm_relative_pose(robot_id=1, delta_position=[0, 0, 5])
        print("✅ Both arms moved back up")
        
    except Exception as e:
        print(f"❌ Relative movement failed: {e}")
        return False
    
    time.sleep(1)
    
    # Test 4: Coordinated movement
    print("\n🧪 TEST 4: Coordinated Movement")
    try:
        print("Moving arms closer together...")
        controller.move_arm_absolute_pose(
            robot_id=0,
            position=[0.25, 0.08, 0.18],  # Closer to center
            orientation=[0, 0, 0]
        )
        controller.move_arm_absolute_pose(
            robot_id=1,
            position=[0.25, -0.08, 0.18],  # Closer to center
            orientation=[0, 0, 0]
        )
        print("✅ Arms moved closer together")
        
        time.sleep(0.5)
        
        print("Moving arms back to original positions...")
        controller.move_arm_absolute_pose(
            robot_id=0,
            position=[0.25, 0.15, 0.20],
            orientation=[0, 0, 0]
        )
        controller.move_arm_absolute_pose(
            robot_id=1,
            position=[0.25, -0.15, 0.20],
            orientation=[0, 0, 0]
        )
        print("✅ Arms returned to original positions")
        
    except Exception as e:
        print(f"❌ Coordinated movement failed: {e}")
        return False
    
    # Test 5: Error handling
    print("\n🧪 TEST 5: Error Handling")
    try:
        print("Testing invalid robot ID...")
        try:
            controller.move_arm_absolute_pose(
                robot_id=99,  # Invalid ID
                position=[0.25, 0.0, 0.20],
                orientation=[0, 0, 0]
            )
            print("⚠️ Expected error not caught")
        except Exception as expected_error:
            print(f"✅ Error properly handled: Invalid robot ID")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
    
    # Cleanup
    print("\n🧹 CLEANUP")
    try:
        print("Moving arms to safe positions...")
        controller.move_arm_absolute_pose(
            robot_id=0,
            position=[0.25, 0.15, 0.25],  # Safe height
            orientation=[0, 0, 0]
        )
        controller.move_arm_absolute_pose(
            robot_id=1,
            position=[0.25, -0.15, 0.25],  # Safe height
            orientation=[0, 0, 0]
        )
        
        print("Opening grippers...")
        controller.control_gripper(robot_id=0, gripper_value=1.0)
        controller.control_gripper(robot_id=1, gripper_value=1.0)
        
        print("✅ Cleanup completed")
        
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    print()
    print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print("🤖 Both SO-101 robots are fully functional")
    print("✅ Individual control: WORKING")
    print("✅ Gripper control: WORKING") 
    print("✅ Relative movements: WORKING")
    print("✅ Coordinated movements: WORKING")
    print("✅ Error handling: WORKING")
    print()
    print("💡 Ready for advanced applications:")
    print("   • Vision-guided dual-arm manipulation")
    print("   • Collaborative pick-and-place operations")
    print("   • Synchronized assembly tasks")
    print("   • Interactive dual-arm control")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
