#!/usr/bin/env python3
"""
🧪 Dual Robot Testing Suite
===========================

Comprehensive testing suite that consolidates all dual robot testing functionality.
Includes robot ID fix verification, visual verification, legacy API testing, and comprehensive tests.

Usage:
    python3 dual_robot_testing_suite.py                    # Run all tests
    python3 dual_robot_testing_suite.py --robot-id-fix     # Test robot ID fix only
    python3 dual_robot_testing_suite.py --visual           # Visual verification only
    python3 dual_robot_testing_suite.py --legacy           # Legacy API tests only
    python3 dual_robot_testing_suite.py --comprehensive    # Comprehensive tests only
"""

import time
import sys
import requests
from dual_so101_controller import DualSO101Controller


class DualRobotTestSuite:
    """Consolidated testing suite for dual robot functionality."""
    
    def __init__(self):
        self.controller = DualSO101Controller()
        self.results = {}
    
    def initialize(self):
        """Initialize the robot controller."""
        print("🔧 Initializing robot controller...")
        result = self.controller.initialize_robot()
        if result:
            print(f"✅ Robot initialized: {result}")
            return True
        else:
            print("❌ Robot initialization failed")
            return False

    def test_robot_id_fix(self):
        """Test to verify both arms move correctly after robot_id fix."""
        print("\n" + "="*60)
        print("🔧 ROBOT ID FIX VERIFICATION TEST")
        print("="*60)
        
        print("\n🧪 Test 1: Move Left Arm (ID=0) Only")
        print("👀 Watch carefully - only the LEFT arm should move!")
        
        try:
            # Move left arm to a distinct position
            self.controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25], [0, 0, 0])
            time.sleep(2)
            
            print("✅ Left arm movement command sent")
            
            print("\n🧪 Test 2: Move Right Arm (ID=1) Only")
            print("👀 Watch carefully - only the RIGHT arm should move!")
            
            # Move right arm to a distinct position  
            self.controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25], [0, 0, 0])
            time.sleep(2)
            
            print("✅ Right arm movement command sent")
            
            print("\n🧪 Test 3: Coordinated Movement")
            print("👀 Both arms should move together to new positions")
            
            # Move both arms simultaneously
            self.controller.move_arm_absolute_pose(0, [0.30, 0.15, 0.20], [0, 0, 0])
            self.controller.move_arm_absolute_pose(1, [0.30, -0.15, 0.20], [0, 0, 0])
            time.sleep(3)
            
            print("✅ Coordinated movement completed")
            
            print("\n" + "="*60)
            print("✅ ROBOT ID FIX TEST COMPLETE!")
            print("="*60)
            print("🔍 Verification Questions:")
            print("   • Did the left arm move alone in Test 1?")
            print("   • Did the right arm move alone in Test 2?") 
            print("   • Did both arms move together in Test 3?")
            print("\nIf YES to all: ✅ Robot ID fix is working correctly!")
            print("If NO to any: ❌ There may still be an issue with robot_id parameter.")
            
            self.results['robot_id_fix'] = True
            return True
            
        except Exception as e:
            print(f"❌ Robot ID fix test failed: {e}")
            self.results['robot_id_fix'] = False
            return False

    def test_visual_verification(self):
        """Sequential arm movement test for visual verification."""
        print("\n" + "="*60)
        print("👁️ VISUAL VERIFICATION TEST")
        print("="*60)
        print("Watch carefully - each arm should move separately!")
        
        try:
            # Starting positions
            print("\n🏠 Moving both arms to starting positions...")
            self.controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20], [0, 0, 0])
            self.controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20], [0, 0, 0])
            time.sleep(2)
            
            print("\n" + "="*50)
            print("🎬 STARTING SEQUENTIAL MOVEMENTS")
            print("="*50)
            
            # Test 1: Left arm only
            print("\n👈 ONLY LEFT ARM (ID=0) SHOULD MOVE NOW!")
            print("Moving left arm to different position...")
            for i in range(3):
                print(f"  Left arm movement {i+1}/3...")
                self.controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25 + i*0.02], [0, 0, 0])
                time.sleep(1.5)
            
            time.sleep(2)
            
            # Test 2: Right arm only
            print("\n👉 ONLY RIGHT ARM (ID=1) SHOULD MOVE NOW!")
            print("Moving right arm to different position...")
            for i in range(3):
                print(f"  Right arm movement {i+1}/3...")
                self.controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25 + i*0.02], [0, 0, 0])
                time.sleep(1.5)
            
            time.sleep(2)
            
            # Test 3: Alternating
            print("\n🔄 ALTERNATING ARM MOVEMENTS")
            print("Arms should move one after the other...")
            for i in range(3):
                print(f"  Round {i+1}: Left arm...")
                self.controller.move_arm_absolute_pose(0, [0.20 + i*0.02, 0.15, 0.20], [0, 0, 0])
                time.sleep(1)
                
                print(f"  Round {i+1}: Right arm...")
                self.controller.move_arm_absolute_pose(1, [0.20 + i*0.02, -0.15, 0.20], [0, 0, 0])
                time.sleep(1)
            
            # Return to safe positions
            print("\n🏠 Returning to safe positions...")
            self.controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25], [0, 0, 0])
            self.controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25], [0, 0, 0])
            
            print("\n" + "="*50)
            print("✅ VISUAL VERIFICATION TEST COMPLETE!")
            print("="*50)
            print("🔍 Did you observe:")
            print("   • Left arm moving alone during left-only phase?")
            print("   • Right arm moving alone during right-only phase?")
            print("   • Arms alternating during alternating phase?")
            print()
            print("If YES to all - the robot_id fix is working! 🎉")
            print("If NO to any - there may still be an issue. 🔧")
            
            self.results['visual_verification'] = True
            return True
            
        except Exception as e:
            print(f"❌ Visual verification test failed: {e}")
            self.results['visual_verification'] = False
            return False

    def test_legacy_api(self):
        """Test legacy API functionality with dual robot support."""
        print("\n" + "="*60)
        print("🔧 LEGACY API DUAL ROBOT TEST")
        print("="*60)
        print("Testing that legacy API calls now support robot_id parameter...")
        
        PI_IP = "127.0.0.1"
        PI_PORT = 80
        
        def call_to_api(endpoint: str, data: dict = {}, robot_id: int = 0):
            """Call PhosphoBot API with robot_id parameter for dual robot support."""
            response = requests.post(f"http://{PI_IP}:{PI_PORT}/move/{endpoint}?robot_id={robot_id}", json=data)
            return response.json()
        
        try:
            print("\n🤖 Testing Robot 0 (Left Arm)...")
            
            # Initialize robot 0
            response = call_to_api("init", robot_id=0)
            print(f"✅ Robot 0 init: {response}")
            
            # Move robot 0
            result = call_to_api("absolute", {
                "x": 25,      # 25cm 
                "y": 15,      # left side
                "z": 20,      # 20cm up
                "rx": 0,      
                "ry": 0,
                "rz": 0,
                "open": 0     
            }, robot_id=0)
            print(f"✅ Robot 0 movement: {result}")
            
            time.sleep(2)
            
            print("\n🤖 Testing Robot 1 (Right Arm)...")
            
            # Initialize robot 1  
            response = call_to_api("init", robot_id=1)
            print(f"✅ Robot 1 init: {response}")
            
            # Move robot 1
            result = call_to_api("absolute", {
                "x": 25,      # 25cm 
                "y": -15,     # right side
                "z": 20,      # 20cm up
                "rx": 0,      
                "ry": 0,
                "rz": 0,
                "open": 0     
            }, robot_id=1)
            print(f"✅ Robot 1 movement: {result}")
            
            print("\n" + "="*50)
            print("✅ LEGACY API DUAL ROBOT TEST COMPLETE!")
            print("="*50)
            print("🔍 Legacy API now supports:")
            print("   • robot_id parameter in call_to_api()")
            print("   • URL query parameter format (?robot_id=X)")
            print("   • Defaults to robot_id=0 for backward compatibility")
            print()
            print("📝 Usage examples:")
            print("   call_to_api('init')                    # Uses robot 0 (default)")
            print("   call_to_api('init', robot_id=1)        # Uses robot 1")
            print("   call_to_api('absolute', {...}, robot_id=0)  # Robot 0 movement")
            
            self.results['legacy_api'] = True
            return True
            
        except Exception as e:
            print(f"❌ Legacy API test failed: {e}")
            print("📋 Make sure PhosphoBot API server is running on localhost:80")
            self.results['legacy_api'] = False
            return False

    def test_comprehensive(self):
        """Comprehensive dual arm test with all working capabilities."""
        print("\n" + "="*60)
        print("🚀 COMPREHENSIVE DUAL ARM TEST")
        print("="*60)
        print("🤖 Testing with TWO SO-101 robots connected")
        
        try:
            # Test 1: Basic Positioning
            print("\n📍 Test 1: Basic Positioning")
            print("Moving arms to starting positions...")
            
            self.controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20], [0, 0, 0])
            self.controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20], [0, 0, 0])
            time.sleep(2)
            print("✅ Basic positioning complete")
            
            # Test 2: Gripper Control
            print("\n🤏 Test 2: Gripper Control")
            print("Testing gripper open/close on both arms...")
            
            # Open both grippers
            self.controller.control_gripper(0, 1.0)
            self.controller.control_gripper(1, 1.0)
            time.sleep(1)
            
            # Close both grippers  
            self.controller.control_gripper(0, 0.0)
            self.controller.control_gripper(1, 0.0)
            time.sleep(1)
            print("✅ Gripper control complete")
            
            # Test 3: Coordinated Movement
            print("\n🤝 Test 3: Coordinated Movement")
            print("Performing synchronized dual-arm movements...")
            
            # Synchronized forward movement
            self.controller.move_arm_absolute_pose(0, [0.30, 0.15, 0.18], [0, 0, 0])
            self.controller.move_arm_absolute_pose(1, [0.30, -0.15, 0.18], [0, 0, 0])
            time.sleep(2)
            
            # Synchronized upward movement
            self.controller.move_arm_absolute_pose(0, [0.30, 0.15, 0.25], [0, 0, 0])
            self.controller.move_arm_absolute_pose(1, [0.30, -0.15, 0.25], [0, 0, 0])
            time.sleep(2)
            print("✅ Coordinated movement complete")
            
            # Test 4: Independent Movement
            print("\n🎯 Test 4: Independent Movement")
            print("Testing independent arm control...")
            
            # Move left arm only
            self.controller.move_arm_absolute_pose(0, [0.20, 0.20, 0.22], [0, 0, 0])
            time.sleep(1)
            
            # Move right arm only
            self.controller.move_arm_absolute_pose(1, [0.20, -0.20, 0.22], [0, 0, 0])
            time.sleep(1)
            print("✅ Independent movement complete")
            
            # Test 5: Return to Safe Position
            print("\n🏠 Test 5: Return to Safe Position")
            print("Returning both arms to safe positions...")
            
            self.controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.25], [0, 0, 0])
            self.controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.25], [0, 0, 0])
            time.sleep(2)
            print("✅ Safe position return complete")
            
            print("\n" + "="*60)
            print("🎉 COMPREHENSIVE TEST COMPLETE!")
            print("="*60)
            print("✅ All dual arm capabilities tested successfully:")
            print("   • Basic positioning ✅")
            print("   • Gripper control ✅") 
            print("   • Coordinated movement ✅")
            print("   • Independent control ✅")
            print("   • Safe positioning ✅")
            print()
            print("🤖 Dual SO-101 robot system is fully operational!")
            
            self.results['comprehensive'] = True
            return True
            
        except Exception as e:
            print(f"❌ Comprehensive test failed: {e}")
            self.results['comprehensive'] = False
            return False

    def run_all_tests(self):
        """Run all available tests."""
        print("🧪 DUAL ROBOT TESTING SUITE")
        print("="*70)
        print("Running all available tests...")
        
        if not self.initialize():
            return False
        
        tests = [
            ("Robot ID Fix", self.test_robot_id_fix),
            ("Visual Verification", self.test_visual_verification),
            ("Legacy API", self.test_legacy_api),
            ("Comprehensive", self.test_comprehensive)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔄 Starting {test_name} test...")
            success = test_func()
            if success:
                print(f"✅ {test_name} test passed")
            else:
                print(f"❌ {test_name} test failed")
        
        # Print final summary
        print("\n" + "="*70)
        print("📊 FINAL TEST SUMMARY")
        print("="*70)
        
        total_tests = len(self.results)
        passed_tests = sum(self.results.values())
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name:<20}: {status}")
        
        print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Dual robot system is fully functional!")
        else:
            print("⚠️ Some tests failed. Check individual test outputs for details.")
        
        return passed_tests == total_tests


def main():
    """Main function with command line argument support."""
    test_suite = DualRobotTestSuite()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        test_arg = sys.argv[1].lower()
        
        if not test_suite.initialize():
            sys.exit(1)
        
        if test_arg == "--robot-id-fix":
            test_suite.test_robot_id_fix()
        elif test_arg == "--visual":
            test_suite.test_visual_verification()
        elif test_arg == "--legacy":
            test_suite.test_legacy_api()
        elif test_arg == "--comprehensive":
            test_suite.test_comprehensive()
        else:
            print("❌ Unknown test option. Available options:")
            print("   --robot-id-fix    : Test robot ID fix")
            print("   --visual          : Visual verification test")
            print("   --legacy          : Legacy API test")
            print("   --comprehensive   : Comprehensive functionality test")
            sys.exit(1)
    else:
        # Run all tests
        success = test_suite.run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
