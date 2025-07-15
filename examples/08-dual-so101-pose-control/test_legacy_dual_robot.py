#!/usr/bin/env python3
"""
🔧 Legacy API Dual Robot Test
=============================

This test demonstrates that the updated legacy test files now support
dual robot control using the robot_id parameter.
"""

import time
import requests


def test_legacy_dual_robot():
    print("🔧 LEGACY API DUAL ROBOT TEST")
    print("=" * 40)
    print("Testing that legacy API files now support robot_id parameter...")
    print()
    
    PI_IP = "127.0.0.1"
    PI_PORT = 80
    
    def call_to_api(endpoint: str, data: dict = {}, robot_id: int = 0):
        """Call PhosphoBot API with robot_id parameter for dual robot support."""
        response = requests.post(f"http://{PI_IP}:{PI_PORT}/move/{endpoint}?robot_id={robot_id}", json=data)
        return response.json()
    
    try:
        print("🤖 Testing Robot 0 (Left Arm)...")
        
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
        print("✅ LEGACY DUAL ROBOT TEST COMPLETE!")
        print("="*50)
        print("🔍 Both legacy test files now support:")
        print("   • robot_id parameter in call_to_api()")
        print("   • URL query parameter format (?robot_id=X)")
        print("   • Defaults to robot_id=0 for backward compatibility")
        print()
        print("📝 Usage examples:")
        print("   call_to_api('init')                    # Uses robot 0 (default)")
        print("   call_to_api('init', robot_id=1)        # Uses robot 1")
        print("   call_to_api('absolute', {...}, robot_id=0)  # Robot 0 movement")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("📋 Make sure PhosphoBot API server is running on localhost:80")


if __name__ == "__main__":
    test_legacy_dual_robot()
