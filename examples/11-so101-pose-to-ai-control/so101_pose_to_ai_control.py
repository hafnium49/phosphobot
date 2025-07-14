#!/usr/bin/env python3
"""
SO-101 Robot Pose to AI Control Script

This script demonstrates how to:
1. Move an SO-101 robot to a specific pose
2. Switch to AI model control (ACT, GR00T, or ACT_BBOX)
3. Handle the transition safely

Usage:
    python so101_pose_to_ai_control.py --robot-id 0 --model-type ACT --model-id "your-model-id"
"""

import argparse
import asyncio
import time
import httpx
import sys
from typing import Literal, Optional, List
import json

class SO101PoseToAIController:
    """Controller to move SO-101 to pose and switch to AI control."""
    
    def __init__(self, server_url: str = "http://localhost:80"):
        self.server_url = server_url
        self.client = httpx.Client(base_url=server_url, timeout=30.0)
        
    def check_connection(self) -> bool:
        """Check if phosphobot server is accessible."""
        try:
            response = self.client.get("/status")
            response.raise_for_status()
            status_data = response.json()
            print(f"✅ Connected to phosphobot server")
            print(f"📊 Server status: {status_data.get('status', 'unknown')}")
            print(f"🤖 Available robots: {status_data.get('robots', [])}")
            return True
        except httpx.RequestError as e:
            print(f"❌ Failed to connect to phosphobot server: {e}")
            return False
            
    def get_robot_status(self, robot_id: int) -> Optional[dict]:
        """Get current robot status and pose."""
        try:
            response = self.client.get("/status")
            response.raise_for_status()
            status_data = response.json()
            
            robots = status_data.get('robot_status', [])
            if robot_id < len(robots):
                robot_info = robots[robot_id]
                print(f"🤖 Robot {robot_id} ({robot_info.get('name', 'unknown')}):")
                print(f"   Type: {robot_info.get('robot_type', 'unknown')}")
                print(f"   Device: {robot_info.get('device_name', 'unknown')}")
                return robot_info
            else:
                print(f"❌ Robot {robot_id} not found")
                return None
        except httpx.RequestError as e:
            print(f"❌ Failed to get robot status: {e}")
            return None
            
    def initialize_robot(self, robot_id: int) -> bool:
        """Initialize the robot connection."""
        try:
            response = self.client.post("/move/init", json={"robot_id": robot_id})
            response.raise_for_status()
            print(f"✅ Robot {robot_id} initialized")
            return True
        except httpx.RequestError as e:
            print(f"❌ Failed to initialize robot {robot_id}: {e}")
            return False
            
    def get_current_pose(self, robot_id: int) -> Optional[dict]:
        """Get current pose of the robot."""
        try:
            response = self.client.get("/pose")
            response.raise_for_status()
            pose_data = response.json()
            
            if isinstance(pose_data, list) and len(pose_data) > robot_id:
                current_pose = pose_data[robot_id]
            elif isinstance(pose_data, dict):
                current_pose = pose_data
            else:
                current_pose = {"x": 0, "y": 0, "z": 0, "rx": 0, "ry": 0, "rz": 0}
                
            print(f"📍 Current pose for robot {robot_id}:")
            print(f"   Position: ({current_pose.get('x', 0):.3f}, {current_pose.get('y', 0):.3f}, {current_pose.get('z', 0):.3f}) m")
            print(f"   Orientation: ({current_pose.get('rx', 0):.1f}, {current_pose.get('ry', 0):.1f}, {current_pose.get('rz', 0):.1f}) deg")
            return current_pose
        except httpx.RequestError as e:
            print(f"❌ Failed to get current pose: {e}")
            return None
            
    def move_to_pose(
        self, 
        robot_id: int,
        position: List[float],  # [x, y, z] in meters
        orientation: Optional[List[float]] = None,  # [rx, ry, rz] in degrees
        gripper_open: bool = False
    ) -> bool:
        """Move robot to specified pose."""
        try:
            payload = {
                "x": position[0],
                "y": position[1],
                "z": position[2],
                "robot_id": robot_id,
                "open": 1 if gripper_open else 0,
                "position_tolerance": 0.01,
                "orientation_tolerance": 5.0,
                "max_trials": 3
            }
            
            if orientation:
                payload.update({
                    "rx": orientation[0],
                    "ry": orientation[1],
                    "rz": orientation[2]
                })
                
            print(f"🎯 Moving robot {robot_id} to pose:")
            print(f"   Position: ({position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f}) m")
            if orientation:
                print(f"   Orientation: ({orientation[0]:.1f}, {orientation[1]:.1f}, {orientation[2]:.1f}) deg")
            print(f"   Gripper: {'open' if gripper_open else 'closed'}")
            
            response = self.client.post("/move/absolute", json=payload)
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ Robot {robot_id} moved to target pose")
            return True
            
        except httpx.RequestError as e:
            print(f"❌ Failed to move robot {robot_id}: {e}")
            return False
            
    def enable_torque(self, robot_id: int) -> bool:
        """Enable robot torque."""
        try:
            response = self.client.post("/torque/toggle", json={
                "torque_status": True,
                "robot_id": robot_id
            })
            response.raise_for_status()
            print(f"⚡ Torque enabled for robot {robot_id}")
            return True
        except httpx.RequestError as e:
            print(f"❌ Failed to enable torque for robot {robot_id}: {e}")
            return False
            
    def disable_torque(self, robot_id: int) -> bool:
        """Disable robot torque."""
        try:
            response = self.client.post("/torque/toggle", json={
                "torque_status": False,
                "robot_id": robot_id
            })
            response.raise_for_status()
            print(f"🔌 Torque disabled for robot {robot_id}")
            return True
        except httpx.RequestError as e:
            print(f"❌ Failed to disable torque for robot {robot_id}: {e}")
            return False
            
    def start_ai_control(
        self,
        robot_ids: List[int],
        model_type: Literal["gr00t", "ACT", "ACT_BBOX"],
        model_id: str,
        cameras_keys_mapping: Optional[dict] = None,
        prompt: Optional[str] = None,
        selected_camera_id: Optional[int] = None
    ) -> bool:
        """Start AI control with specified model."""
        try:
            payload = {
                "robot_ids": robot_ids,
                "model_type": model_type,
                "model_id": model_id,
                "init_connected_robots": True,
                "verify_cameras": True
            }
            
            if cameras_keys_mapping:
                payload["cameras_keys_mapping"] = cameras_keys_mapping
            if prompt:
                payload["prompt"] = prompt
            if selected_camera_id is not None:
                payload["selected_camera_id"] = selected_camera_id
                
            print(f"🤖 Starting AI control:")
            print(f"   Model type: {model_type}")
            print(f"   Model ID: {model_id}")
            print(f"   Robot IDs: {robot_ids}")
            if prompt:
                print(f"   Prompt: {prompt}")
                
            response = self.client.post("/ai/start", json=payload)
            response.raise_for_status()
            result = response.json()
            
            ai_control_id = result.get("ai_control_id")
            print(f"✅ AI control started (ID: {ai_control_id})")
            return True
            
        except httpx.RequestError as e:
            print(f"❌ Failed to start AI control: {e}")
            print("💡 Make sure the model ID is valid and cameras are properly configured")
            return False
            
    def stop_ai_control(self) -> bool:
        """Stop AI control."""
        try:
            response = self.client.post("/ai/stop")
            response.raise_for_status()
            print("🛑 AI control stopped")
            return True
        except httpx.RequestError as e:
            print(f"❌ Failed to stop AI control: {e}")
            return False
            
    def close(self):
        """Close the HTTP client."""
        self.client.close()


def main():
    parser = argparse.ArgumentParser(description="Move SO-101 to pose and switch to AI control")
    parser.add_argument("--robot-id", type=int, default=0, help="Robot ID (default: 0)")
    parser.add_argument("--model-type", type=str, choices=["gr00t", "ACT", "ACT_BBOX"], 
                       default="ACT", help="AI model type (default: ACT)")
    parser.add_argument("--model-id", type=str, required=True, help="Hugging Face model ID")
    parser.add_argument("--server-url", type=str, default="http://localhost:80", 
                       help="Phosphobot server URL (default: http://localhost:80)")
    
    # Pose parameters
    parser.add_argument("--position", type=float, nargs=3, default=[0.25, 0.0, 0.15],
                       help="Target position [x, y, z] in meters (default: [0.25, 0.0, 0.15])")
    parser.add_argument("--orientation", type=float, nargs=3, default=[0, 0, 0],
                       help="Target orientation [rx, ry, rz] in degrees (default: [0, 0, 0])")
    parser.add_argument("--gripper-open", action="store_true", help="Open gripper")
    
    # AI control parameters
    parser.add_argument("--prompt", type=str, help="Task prompt for AI model")
    parser.add_argument("--camera-id", type=int, help="Camera ID for ACT_BBOX models")
    parser.add_argument("--skip-pose", action="store_true", help="Skip pose movement, go directly to AI control")
    
    args = parser.parse_args()
    
    print("🤖 SO-101 Pose to AI Control Script")
    print("=" * 40)
    
    controller = SO101PoseToAIController(args.server_url)
    
    try:
        # Check connection
        if not controller.check_connection():
            print("💡 Make sure phosphobot server is running: phosphobot run")
            return 1
            
        # Get robot status
        robot_info = controller.get_robot_status(args.robot_id)
        if not robot_info:
            return 1
            
        # Initialize robot
        if not controller.initialize_robot(args.robot_id):
            return 1
            
        # Get current pose
        current_pose = controller.get_current_pose(args.robot_id)
        
        if not args.skip_pose:
            print("\n📍 STEP 1: Moving to target pose")
            print("-" * 30)
            
            # Enable torque
            if not controller.enable_torque(args.robot_id):
                return 1
                
            # Move to specified pose
            if not controller.move_to_pose(
                args.robot_id, 
                args.position, 
                args.orientation,
                args.gripper_open
            ):
                return 1
                
            # Wait for movement to complete
            print("⏳ Waiting for movement to complete...")
            time.sleep(3)
            
            # Verify final pose
            final_pose = controller.get_current_pose(args.robot_id)
        
        print("\n🤖 STEP 2: Starting AI control")
        print("-" * 30)
        
        # Prepare for AI control
        robot_ids = [args.robot_id]
        
        # Validate model type specific requirements
        if args.model_type == "ACT_BBOX" and args.camera_id is None:
            print("❌ Camera ID is required for ACT_BBOX models")
            print("💡 Use --camera-id to specify which camera to use")
            return 1
            
        # Start AI control
        if not controller.start_ai_control(
            robot_ids=robot_ids,
            model_type=args.model_type,
            model_id=args.model_id,
            prompt=args.prompt,
            selected_camera_id=args.camera_id
        ):
            return 1
            
        print("\n✅ SUCCESS: AI control is now active!")
        print("-" * 40)
        print("🎯 The robot is now under AI model control")
        print("📹 Make sure cameras are properly positioned")
        print("🛑 To stop AI control, use: curl -X POST http://localhost:80/ai/stop")
        print("💻 Or use the web interface at http://localhost:80")
        
        # Keep script running to monitor (optional)
        try:
            print("\n⌨️  Press Ctrl+C to stop monitoring and exit...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping AI control...")
            controller.stop_ai_control()
            print("👋 Goodbye!")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
        
    finally:
        controller.close()
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
