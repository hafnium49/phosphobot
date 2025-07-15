#!/usr/bin/env python3
"""
Single Arm SO-101 Test - Corrected Version

Tests the corrected dual_so101_controller.py with proper API integration.
This version uses the fixed controller that handles coordinate conversion,
proper HTTP client, and single robot support.
"""

import time
from dual_so101_controller import DualSO101Controller


def test_corrected_controller():
    """Test the corrected dual SO-101 controller with single robot."""
    print("🧪 Testing Corrected SO-101 Controller")
    print("=====================================")
    
    # Initialize controller
    controller = DualSO101Controller()
    
    try:
        # Initialize robot
        print("\n🔧 Initializing robot...")
        result = controller.initialize_robot()
        if result:
            print(f"✅ Initialization successful: {result}")
        else:
            print("❌ Initialization failed")
            return
        
        time.sleep(2)
        
        # Test absolute movement (coordinates in meters, will be converted to cm)
        print("\n📍 Testing absolute movement...")
        print("Moving to position [0.25m, 0.0m, 0.20m] (converted to cm internally)")
        controller.move_arm_absolute_pose(0, [0.25, 0.0, 0.20])
        time.sleep(2)
        
        # Test gripper control  
        print("\n✋ Testing gripper control...")
        controller.control_gripper(0, 1.0)  # Open
        time.sleep(1)
        controller.control_gripper(0, 0.0)  # Close
        time.sleep(1)
        
        # Test relative movement (in centimeters)
        print("\n🔄 Testing relative movement...")
        print("Moving 5cm in x and z directions")
        controller.move_arm_relative_pose(0, [5, 0, 5])  # 5cm movements
        time.sleep(2)
        
        # Return to center
        print("\n🏠 Returning to center position...")
        controller.move_arm_absolute_pose(0, [0.25, 0.0, 0.20])
        time.sleep(2)
        
        print("\n✅ All tests completed successfully!")
        print("🎉 The corrected controller is working properly!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        controller.close()


def test_legacy_api():
    """Test direct API calls to verify endpoints are working."""
    import requests
    
    print("\n🔧 Testing Legacy API Calls")
    print("===========================")
    
    PI_IP = "127.0.0.1"
    PI_PORT = 80
    
    def call_to_api(endpoint: str, data: dict = {}):
        """Call PhosphoBot API using the same format as other working examples."""
        response = requests.post(f"http://{PI_IP}:{PI_PORT}/move/{endpoint}", json=data)
        return response.json()
    
    try:
        # Initialize robot
        print("Initializing with legacy API...")
        response = call_to_api("init")
        print(f"✅ Legacy init result: {response}")
        
        # Test basic movement
        print("Testing basic movement with legacy API...")
        result = call_to_api("absolute", {
            "x": 25,      # 25cm 
            "y": 0,       # center
            "z": 20,      # 20cm up
            "rx": 0,      
            "ry": 0,
            "rz": 0,
            "open": 0     
        })
        print(f"✅ Legacy movement result: {result}")
        
    except Exception as e:
        print(f"❌ Legacy API test failed: {e}")


if __name__ == "__main__":
    # Test the corrected controller
    test_corrected_controller()
    
    # Test legacy API for comparison  
    test_legacy_api()
