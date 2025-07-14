#!/usr/bin/env python3
"""
Single Arm SO-101 Test

Modified version of dual arm control to work with single arm setup.
Uses the correct PhosphoBot API endpoints that we know work.
"""

import time
import requests

# Robot API Configuration
PI_IP = "127.0.0.1"
PI_PORT = 80


def call_to_api(endpoint: str, data: dict = {}):
    """Call PhosphoBot API using the same format as other working examples."""
    response = requests.post(f"http://{PI_IP}:{PI_PORT}/move/{endpoint}", json=data)
    return response.json()


def main():
    print("🤖 Single SO-101 Arm Control Test")
    print("=================================")
    
    try:
        # Initialize robot
        print("\n🔄 Initializing robot...")
        response = call_to_api("init")
        print(f"✅ Robot initialized: {response}")
        
        print("\n🎯 Testing basic pose movements...")
        
        # Move to position 1
        print("Moving to position 1...")
        result1 = call_to_api("absolute", {
            "x": 25,      # 25cm forward
            "y": 15,      # 15cm right  
            "z": 15,      # 15cm up
            "rx": 0,      # No rotation
            "ry": 0,
            "rz": 0,
            "open": 0     # Gripper closed
        })
        print(f"✅ Position 1 result: {result1}")
        time.sleep(2)
        
        # Move to position 2
        print("Moving to position 2...")
        result2 = call_to_api("absolute", {
            "x": 25,      # 25cm forward
            "y": -15,     # 15cm left
            "z": 15,      # 15cm up
            "rx": 0,      # No rotation
            "ry": 0,
            "rz": 0,
            "open": 1     # Gripper open
        })
        print(f"✅ Position 2 result: {result2}")
        time.sleep(2)
        
        # Test gripper control
        print("\n🤏 Testing gripper control...")
        
        # Close gripper
        print("Closing gripper...")
        result3 = call_to_api("absolute", {
            "x": 25,      # Maintain position
            "y": -15,     
            "z": 15,      
            "rx": 0,      
            "ry": 0,
            "rz": 0,
            "open": 0     # Close gripper
        })
        print(f"✅ Gripper closed: {result3}")
        time.sleep(1)
        
        # Open gripper
        print("Opening gripper...")
        result4 = call_to_api("absolute", {
            "x": 25,      # Maintain position
            "y": -15,     
            "z": 15,      
            "rx": 0,      
            "ry": 0,
            "rz": 0,
            "open": 1     # Open gripper
        })
        print(f"✅ Gripper opened: {result4}")
        time.sleep(1)
        
        # Return to center
        print("\n🏠 Returning to center position...")
        result5 = call_to_api("absolute", {
            "x": 20,      # 20cm forward
            "y": 0,       # Center
            "z": 10,      # 10cm up
            "rx": 0,      
            "ry": 0,
            "rz": 0,
            "open": 0     # Close gripper
        })
        print(f"✅ Returned to center: {result5}")
        
        print("\n✅ Single arm test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
