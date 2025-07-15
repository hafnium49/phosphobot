#!/usr/bin/env python3
"""
Test script to verify the wave motion works
"""

import requests
import time

def call_to_api(endpoint: str, data: dict = {}):
    response = requests.post(f"http://127.0.0.1:80/move/{endpoint}", json=data)
    return response.json()

def wave_motion():
    print("👋 Testing wave motion...")
    points = 5
    for wave_cycle in range(2):
        print(f"Wave cycle {wave_cycle + 1}/2")
        for i in range(points):
            position = {
                "x": 0,
                "y": 20 * (-1) ** i,  # Increased wave amplitude
                "z": 30,              # Higher position
                "rx": -90,
                "ry": 0,
                "rz": 0,
                "open": i % 2 == 0,
            }
            print(f"  Position {i+1}: Y={position['y']}, Open={position['open']}")
            
            try:
                response = call_to_api("absolute", position)
                print(f"    ✅ Response: {response}")
            except Exception as e:
                print(f"    ❌ Error: {e}")
                
            time.sleep(0.3)

def main():
    print("🤖 Testing SO-101 Wave Motion")
    print("=" * 35)
    
    # Initialize robot
    try:
        response = call_to_api("init")
        print(f"✅ Robot initialized: {response}")
    except Exception as e:
        print(f"❌ Init failed: {e}")
        return
    
    time.sleep(1)
    
    # Test wave motion
    wave_motion()
    
    print("\n🏁 Wave motion test completed!")

if __name__ == "__main__":
    main()
