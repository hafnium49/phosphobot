#!/usr/bin/env python3
"""
Test script for voice commands without audio recording.
This simulates the voice command functionality to test the API endpoints.
"""

import requests
import argparse
import sys

def api_call(endpoint: str, data: dict | None = None):
    """Make API call to the phosphobot server."""
    try:
        response = requests.post(
            f"http://localhost:80/{endpoint}",
            json=data,
        )
        print(f"API call to {endpoint}: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
        return response
    except requests.RequestException as e:
        print(f"Failed to send data to {endpoint}: {e}")
        return None

def move_box_left():
    """Simulate moving box left - using a simple movement instead of recording."""
    print("🔄 Simulating: Moving box left")
    # Use relative movement as substitute for recorded movement
    response = api_call("move/relative", {
        "x": 0, "y": 5, "z": 0, "rx": 0, "ry": 0, "rz": 0, 
        "open": 0, "robot_id": 1
    })
    return response is not None

def move_box_right():
    """Simulate moving box right - using a simple movement instead of recording."""
    print("🔄 Simulating: Moving box right")
    # Use relative movement as substitute for recorded movement  
    response = api_call("move/relative", {
        "x": 0, "y": -5, "z": 0, "rx": 0, "ry": 0, "rz": 0, 
        "open": 0, "robot_id": 1
    })
    return response is not None

def say_hello():
    """Simulate waving - using a simple movement instead of recording."""
    print("🔄 Simulating: Waving hello")
    # Use relative movement as substitute for recorded movement
    response = api_call("move/relative", {
        "x": 0, "y": 0, "z": 3, "rx": 0, "ry": 0, "rz": 0, 
        "open": 1, "robot_id": 1
    })
    return response is not None

def decide_action(prompt: str):
    """Decide which action to take based on the text prompt."""
    prompt = prompt.lower()
    
    if "left" in prompt or "that" in prompt:
        move_box_left()
        print("✅ Executed: Moving box left")
    elif "right" in prompt or "write" in prompt or "riots" in prompt:
        move_box_right()
        print("✅ Executed: Moving box right")
    elif (
        "wave" in prompt
        or "hello" in prompt
        or "say" in prompt
        or "what" in prompt
        or "wait" in prompt
        or "ways" in prompt
    ):
        say_hello()
        print("✅ Executed: Waving")
    else:
        print("❌ No action taken for:", prompt)

def test_voice_commands():
    """Test the voice command system with simulated text input."""
    print("🤖 Testing Voice Command System (without audio)")
    print("=" * 50)
    
    # Initialize robot
    print("\n1. Initializing robot...")
    if api_call("move/init"):
        print("✅ Robot initialized successfully")
    else:
        print("❌ Failed to initialize robot")
        return
    
    # Test various commands
    test_commands = [
        "move left",
        "go right", 
        "wave hello",
        "invalid command",
        "left that way",
        "write something", # should trigger "right"
        "say hello"
    ]
    
    print(f"\n2. Testing {len(test_commands)} voice commands...")
    for i, command in enumerate(test_commands, 1):
        print(f"\n   Test {i}: '{command}'")
        decide_action(command)
    
    print("\n✅ Voice command testing completed!")

def interactive_test():
    """Interactive test mode where user can type commands."""
    print("🎤 Interactive Voice Command Test")
    print("=" * 40)
    print("Available commands:")
    print("  - 'left' or 'that': Move box left")
    print("  - 'right', 'write', 'riots': Move box right") 
    print("  - 'wave', 'hello', 'say', 'what', 'wait', 'ways': Wave")
    print("  - 'quit' or 'exit': Exit the program")
    print()
    
    # Initialize robot
    if not api_call("move/init"):
        print("❌ Failed to initialize robot")
        return
    
    while True:
        try:
            command = input("Enter voice command (or 'quit'): ").strip()
            if command.lower() in ['quit', 'exit', 'q']:
                break
            if command:
                decide_action(command)
        except KeyboardInterrupt:
            break
    
    print("\n👋 Goodbye!")

def main():
    parser = argparse.ArgumentParser(description='Test voice commands without audio')
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    parser.add_argument(
        '--robot-id',
        type=int,
        default=1,
        help='Robot ID to control (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Set global robot ID for the movements
    global robot_id
    robot_id = args.robot_id
    
    print(f"Using robot ID: {robot_id}")
    
    if args.interactive:
        interactive_test()
    else:
        test_voice_commands()

if __name__ == "__main__":
    main()
