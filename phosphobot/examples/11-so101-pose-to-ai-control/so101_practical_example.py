#!/usr/bin/env python3
"""
SO-101 Practical Example: Pose Control to AI Model

This script demonstrates a real working example using:
- SO-101 robot pose control
- Real HuggingFace ACT model: LegrandFrederic/Orange-brick-in-black-box
- Actual camera and robot integration

Usage:
    python so101_practical_example.py
"""

import httpx
import time
import sys
import numpy as np
from typing import List, Optional

class SO101PracticalController:
    """Real-world controller for SO-101 robot with AI model integration."""
    
    def __init__(self, server_url: str = "http://localhost:80"):
        self.server_url = server_url
        self.client = httpx.Client(base_url=server_url, timeout=30.0)
        
    def check_robot_status(self) -> bool:
        """Check if robot and cameras are available."""
        try:
            response = self.client.get("/status")
            response.raise_for_status()
            status = response.json()
            
            print("🤖 System Status:")
            print(f"   Server: {status.get('status', 'unknown')}")
            print(f"   Robots: {status.get('robots', [])}")
            print(f"   Cameras: {len(status.get('cameras', {}).get('video_cameras_ids', []))} available")
            print(f"   AI Status: {status.get('ai_running_status', 'unknown')}")
            
            has_robot = len(status.get('robots', [])) > 0
            has_cameras = len(status.get('cameras', {}).get('video_cameras_ids', [])) >= 3
            
            return has_robot and has_cameras
            
        except httpx.RequestError as e:
            print(f"❌ Cannot connect to phosphobot server: {e}")
            return False
            
    def move_to_observation_pose(self) -> bool:
        """Move robot to a good pose for camera observation."""
        try:
            # Good observation pose for the model
            payload = {
                "x": 0.25,
                "y": 0.0, 
                "z": 0.20,
                "rx": 0,
                "ry": -15,
                "rz": 0,
                "robot_id": 0,
                "open": 0,
                "position_tolerance": 0.01,
                "orientation_tolerance": 5.0
            }
            
            print("🎯 Moving to observation pose...")
            print(f"   Position: ({payload['x']}, {payload['y']}, {payload['z']}) m")
            print(f"   Orientation: ({payload['rx']}, {payload['ry']}, {payload['rz']}) deg")
            
            response = self.client.post("/move/absolute", json=payload)
            response.raise_for_status()
            
            print("✅ Robot moved to observation pose")
            return True
            
        except httpx.RequestError as e:
            print(f"❌ Failed to move robot: {e}")
            return False
            
    def start_ai_model(self) -> bool:
        """Start the real ACT model for object manipulation."""
        try:
            # Real working model from HuggingFace
            model_config = {
                "robot_ids": [0],
                "model_type": "ACT",
                "model_id": "LegrandFrederic/Orange-brick-in-black-box",
                "init_connected_robots": True,
                "verify_cameras": True,
                "cameras_keys_mapping": {
                    "observation.images.main": 0,
                    "observation.images.wrist": 1, 
                    "observation.images.side": 2
                }
            }
            
            print("🚀 Starting AI model control...")
            print(f"   Model: {model_config['model_id']}")
            print("   This model was trained for orange brick manipulation tasks")
            print("   It expects 3 cameras: main, wrist, and side views")
            
            response = self.client.post("/ai/start", json=model_config)
            response.raise_for_status()
            result = response.json()
            
            ai_control_id = result.get("ai_control_id")
            print(f"✅ AI model started successfully (ID: {ai_control_id})")
            print("🧠 Robot is now under AI control!")
            
            return True
            
        except httpx.RequestError as e:
            print(f"❌ Failed to start AI model: {e}")
            error_text = e.response.text if hasattr(e, 'response') else str(e)
            if "cameras" in error_text.lower():
                print("💡 Camera issue detected. Make sure 3 cameras are connected")
            elif "model" in error_text.lower():
                print("💡 Model issue detected. Model might be loading or unavailable")
            return False
            
    def monitor_ai_control(self, duration: int = 60):
        """Monitor the AI control for a specified duration."""
        print(f"\n👁️  Monitoring AI control for {duration} seconds...")
        print("🎯 The AI model will attempt to:")
        print("   - Identify orange objects (bricks)")
        print("   - Plan manipulation strategies")
        print("   - Execute pick and place actions")
        print("   - Adapt based on visual feedback")
        print("\nℹ️  Press Ctrl+C to stop early")
        
        try:
            for i in range(duration):
                # Check if AI is still running
                response = self.client.get("/status")
                status = response.json()
                ai_status = status.get('ai_running_status', 'stopped')
                
                if ai_status == 'stopped':
                    print(f"\n⚠️  AI control stopped after {i} seconds")
                    break
                    
                print(f"⏱️  AI active for {i+1}/{duration} seconds (Status: {ai_status})", end='\r')
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n⚠️  Monitoring interrupted by user")
            
    def stop_ai_control(self) -> bool:
        """Stop AI control safely."""
        try:
            response = self.client.post("/ai/stop")
            response.raise_for_status()
            print("🛑 AI control stopped")
            return True
        except httpx.RequestError as e:
            print(f"❌ Failed to stop AI control: {e}")
            return False
            
    def close(self):
        """Clean up resources."""
        self.client.close()

def main():
    print("🤖 SO-101 Practical AI Control Example")
    print("=" * 50)
    print("This script demonstrates real AI model integration using:")
    print("📦 Model: LegrandFrederic/Orange-brick-in-black-box")
    print("🎯 Task: Orange brick manipulation and organization") 
    print("📹 Cameras: 3 camera setup (main, wrist, side)")
    print("🔧 Robot: SO-101 manipulator with pose control")
    print("-" * 50)
    
    controller = SO101PracticalController()
    
    try:
        # Step 1: Check system status
        print("\n📋 STEP 1: System Check")
        if not controller.check_robot_status():
            print("❌ System requirements not met:")
            print("   • Ensure phosphobot server is running: phosphobot run")
            print("   • Connect SO-101 robot")
            print("   • Connect at least 3 cameras")
            return 1
            
        # Step 2: Position robot for optimal camera view
        print("\n📍 STEP 2: Robot Positioning")
        if not controller.move_to_observation_pose():
            print("❌ Failed to position robot")
            return 1
            
        # Wait for movement to settle
        print("⏳ Waiting for robot to settle...")
        time.sleep(3)
        
        # Step 3: Start AI model
        print("\n🧠 STEP 3: AI Model Activation")
        if not controller.start_ai_model():
            print("❌ Failed to start AI model")
            print("💡 Troubleshooting tips:")
            print("   • Check internet connection for model download")
            print("   • Verify camera connections and lighting")
            print("   • Ensure robot is properly initialized")
            return 1
            
        # Step 4: Monitor AI behavior
        print("\n🎯 STEP 4: AI Control Monitoring")
        controller.monitor_ai_control(duration=60)
        
        # Step 5: Clean shutdown
        print("\n🛑 STEP 5: Safe Shutdown")
        controller.stop_ai_control()
        
        print("\n✅ Demo completed successfully!")
        print("-" * 50)
        print("🎉 What just happened:")
        print("   1. Robot moved to optimal observation pose")
        print("   2. AI model loaded and analyzed the scene")
        print("   3. Model planned and executed manipulation actions")
        print("   4. System safely returned to manual control")
        print("\n💡 Next steps:")
        print("   • Try placing orange objects in the workspace")
        print("   • Experiment with different lighting conditions")
        print("   • Explore other available models on HuggingFace")
        print("   • Train your own models using phosphobot datasets")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
        
    finally:
        controller.close()
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
