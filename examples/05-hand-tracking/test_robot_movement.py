#!/usr/bin/env python3
"""
Quick test to verify SO-101 robot movement commands are working
"""

import requests
import time

def test_robot_movement():
    print("🤖 Testing SO-101 Robot Movement Commands")
    print("=" * 45)
    
    # Initialize robot
    try:
        response = requests.post("http://localhost:80/move/init", timeout=5)
        print(f"✅ Robot initialized: {response.json()}")
    except Exception as e:
        print(f"❌ Init failed: {e}")
        return
    
    # Test movements
    test_positions = [
        {"x": 0, "y": 0, "z": 100, "open": 0.5},    # Center high
        {"x": 50, "y": 0, "z": 50, "open": 0.8},    # Right middle
        {"x": -50, "y": 0, "z": 50, "open": 0.2},   # Left middle  
        {"x": 0, "y": 50, "z": 50, "open": 1.0},    # Forward middle
        {"x": 0, "y": -50, "z": 50, "open": 0.0},   # Back middle
        {"x": 0, "y": 0, "z": 80, "open": 0.5},     # Return center
    ]
    
    print("\n🎯 Testing movement commands...")
    for i, pos in enumerate(test_positions):
        print(f"Position {i+1}: X={pos['x']}, Y={pos['y']}, Z={pos['z']}, Open={pos['open']}")
        
        try:
            response = requests.post(
                "http://localhost:80/move/absolute",
                json=pos,
                timeout=3
            )
            
            if response.status_code == 200:
                print(f"  ✅ Success: {response.json()}")
            else:
                print(f"  ❌ Error {response.status_code}: {response.text}")
                
            time.sleep(2)  # Wait for movement
            
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
    
    print("\n🏁 Movement test completed!")

if __name__ == "__main__":
    test_robot_movement()
