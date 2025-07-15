#!/usr/bin/env python3
"""
SO-101 Demo: Predefined Poses to AI Control

This script demonstrates common poses and AI model usage patterns.
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from so101_pose_to_ai_control import SO101PoseToAIController
import time

# Predefined poses for common tasks
DEMO_POSES = {
    "home": {
        "position": [0.25, 0.0, 0.15],
        "orientation": [0, 0, 0],
        "gripper_open": False,
        "description": "Home position - neutral pose"
    },
    "pickup_ready": {
        "position": [0.35, 0.0, 0.05],
        "orientation": [0, 45, 0],
        "gripper_open": True,
        "description": "Ready to pick up objects from table"
    },
    "observation": {
        "position": [0.20, 0.0, 0.25],
        "orientation": [0, -30, 0],
        "gripper_open": False,
        "description": "Good position for camera observation"
    },
    "manipulation": {
        "position": [0.30, 0.1, 0.12],
        "orientation": [0, 30, 15],
        "gripper_open": False,
        "description": "Good position for fine manipulation tasks"
    }
}

# Example AI model configurations
AI_MODEL_CONFIGS = {
    "household_tasks": {
        "model_id": "your-username/household-robot-model",
        "model_type": "ACT",
        "prompt": "Perform household tasks like cleaning and organizing"
    },
    "object_manipulation": {
        "model_id": "your-username/manipulation-model",
        "model_type": "ACT_BBOX",
        "prompt": "Pick up and manipulate objects on the table",
        "camera_id": 0
    },
    "gr00t_demo": {
        "model_id": "nvidia/gr00t-demo-model",
        "model_type": "gr00t",
        "prompt": "Follow natural language instructions for robot control"
    }
}

def run_demo():
    """Run an interactive demo."""
    print("🤖 SO-101 Pose to AI Control Demo")
    print("=" * 50)
    
    controller = SO101PoseToAIController()
    
    try:
        # Check connection
        if not controller.check_connection():
            print("💡 Start the phosphobot server first: phosphobot run")
            return 1
            
        robot_id = 0
        
        # Initialize robot
        if not controller.initialize_robot(robot_id):
            return 1
            
        print("\n📍 Available demo poses:")
        for i, (name, pose) in enumerate(DEMO_POSES.items(), 1):
            print(f"  {i}. {name}: {pose['description']}")
            
        try:
            pose_choice = int(input("\nSelect a pose (1-4): ")) - 1
            pose_names = list(DEMO_POSES.keys())
            
            if 0 <= pose_choice < len(pose_names):
                selected_pose_name = pose_names[pose_choice]
                selected_pose = DEMO_POSES[selected_pose_name]
                
                print(f"\n🎯 Moving to '{selected_pose_name}' pose...")
                
                # Enable torque and move to pose
                controller.enable_torque(robot_id)
                
                success = controller.move_to_pose(
                    robot_id,
                    selected_pose["position"],
                    selected_pose["orientation"],
                    selected_pose["gripper_open"]
                )
                
                if success:
                    print("✅ Pose reached successfully!")
                    time.sleep(2)
                    
                    print("\n🤖 Available AI models:")
                    for i, (name, config) in enumerate(AI_MODEL_CONFIGS.items(), 1):
                        print(f"  {i}. {name} ({config['model_type']}): {config['prompt']}")
                        
                    try:
                        ai_choice = int(input("\nSelect an AI model (1-3): ")) - 1
                        ai_names = list(AI_MODEL_CONFIGS.keys())
                        
                        if 0 <= ai_choice < len(ai_names):
                            selected_ai_name = ai_names[ai_choice]
                            selected_ai = AI_MODEL_CONFIGS[selected_ai_name]
                            
                            print(f"\n🚀 Starting AI control with '{selected_ai_name}'...")
                            print("⚠️  Note: Make sure you have the correct model ID!")
                            print(f"📝 Current model ID: {selected_ai['model_id']}")
                            
                            # Note: In a real scenario, you'd use actual model IDs
                            print("💡 This is a demo - update model IDs in the script for real usage")
                            
                        else:
                            print("❌ Invalid AI model selection")
                            
                    except ValueError:
                        print("❌ Invalid input for AI model selection")
                        
                else:
                    print("❌ Failed to reach target pose")
                    
            else:
                print("❌ Invalid pose selection")
                
        except ValueError:
            print("❌ Invalid input for pose selection")
            
    except Exception as e:
        print(f"❌ Demo error: {e}")
        return 1
        
    finally:
        controller.close()
        
    return 0

if __name__ == "__main__":
    sys.exit(run_demo())
