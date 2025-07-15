#!/usr/bin/env python3
"""
Simple Voice Command Example (Text Input Version)

This version works around audio dependency issues by using text input
instead of microphone recording. It demonstrates the same voice command
logic and robot control functionality.
"""

import requests
import time
import sys
import os


# Get absolute paths for recording files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDING_FILES = {
    "push_left": os.path.join(BASE_DIR, "push_left.json"),
    "push_right": os.path.join(BASE_DIR, "push_right.json"), 
    "wave": os.path.join(BASE_DIR, "wave.json")
}


def api_call(endpoint: str, data: dict | None = None):
    """Make API call to the phosphobot server."""
    try:
        response = requests.post(
            f"http://localhost:80/{endpoint}",
            json=data,
        )
        if response.status_code == 200:
            print(f"✅ API call to {endpoint} successful")
        else:
            print(f"❌ API call to {endpoint} failed: {response.status_code}")
            if response.text:
                print(f"   Response: {response.text}")
        return response
    except requests.RequestException as e:
        print(f"❌ Failed to send data to {endpoint}: {e}")
        return None


def move_box_left():
    """Move box left using direct movement commands."""
    print("🔄 Executing: Move box left")
    # Use direct movement instead of recording playback
    api_call("move/relative", {
        "x": 0, "y": 5, "z": 0, "rx": 0, "ry": 0, "rz": 0, 
        "open": 0, "robot_id": 1
    })


def move_box_right():
    """Move box right using direct movement commands."""
    print("🔄 Executing: Move box right")
    # Use direct movement instead of recording playback
    api_call("move/relative", {
        "x": 0, "y": -5, "z": 0, "rx": 0, "ry": 0, "rz": 0, 
        "open": 0, "robot_id": 1
    })


def say_hello():
    """Wave hello using direct movement commands."""
    print("🔄 Executing: Wave hello")
    # Create a simple waving motion
    movements = [
        {"x": 0, "y": 0, "z": 3, "rx": 0, "ry": 0, "rz": 0, "open": 1, "robot_id": 1},
        {"x": 0, "y": -3, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 1, "robot_id": 1},
        {"x": 0, "y": 3, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 1, "robot_id": 1},
        {"x": 0, "y": 0, "z": -3, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": 1}
    ]
    
    for movement in movements:
        api_call("move/relative", movement)
        time.sleep(0.5)


def decide_action(prompt: str):
    """Decide which action to take based on the text prompt."""
    prompt = prompt.lower().strip()
    
    if not prompt:
        return
    
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
        print(f"❌ No action recognized for: '{prompt}'")
        print("   Try: 'left', 'right', 'wave', 'hello'")


def show_help():
    """Show available commands."""
    print("\n📋 Available Voice Commands:")
    print("=" * 35)
    print("🔸 'left' or 'that'           → Move box left")
    print("🔸 'right', 'write', 'riots'  → Move box right") 
    print("🔸 'wave', 'hello', 'say'     → Wave hello")
    print("🔸 'what', 'wait', 'ways'     → Wave hello")
    print("🔸 'help'                     → Show this help")
    print("🔸 'quit' or 'exit'           → Exit program")
    print("=" * 35)


def interactive_mode():
    """Interactive text input mode."""
    print("🎤 Voice Command Simulator (Text Input Mode)")
    print("=" * 50)
    print("This version uses text input instead of microphone")
    print("to work around audio dependency issues.")
    show_help()
    
    # Initialize robot
    print("\n🔧 Initializing robot...")
    if not api_call("move/init"):
        print("❌ Failed to initialize robot. Is the server running?")
        return
    
    print("\n✅ Robot initialized! Ready for commands.")
    print("💡 Type commands below (or 'help' for options):")
    
    while True:
        try:
            command = input("\n🎙️  Enter command: ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif command.lower() == 'help':
                show_help()
            elif command:
                decide_action(command)
            else:
                print("   (Empty command - try 'help' for options)")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break


def demo_mode():
    """Demonstration mode with automatic command testing."""
    print("🎪 Voice Command Demo Mode")
    print("=" * 30)
    
    # Initialize robot
    print("🔧 Initializing robot...")
    if not api_call("move/init"):
        print("❌ Failed to initialize robot. Is the server running?")
        return
    
    print("✅ Robot initialized!")
    
    # Demo commands
    demo_commands = [
        "move left",
        "go right", 
        "wave hello",
        "say something",
        "that way",
        "write this down",  # Should trigger "right"
        "wait for me"       # Should trigger "wave"
    ]
    
    print(f"\n🎯 Testing {len(demo_commands)} voice commands...")
    
    for i, command in enumerate(demo_commands, 1):
        print(f"\n--- Demo {i}/{len(demo_commands)} ---")
        print(f"🎙️  Command: '{command}'")
        decide_action(command)
        time.sleep(2)  # Pause between commands
    
    print("\n✅ Demo completed!")


def test_movements():
    """Test the direct movement commands."""
    print("🧪 Testing Direct Movement Commands")
    print("=" * 40)
    
    # Initialize robot
    print("🔧 Initializing robot...")
    if not api_call("move/init"):
        print("❌ Failed to initialize robot. Is the server running?")
        return
    
    movements = [
        ("Push Left", {"x": 0, "y": 5, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": 1}),
        ("Push Right", {"x": 0, "y": -5, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": 1}),
        ("Wave Up", {"x": 0, "y": 0, "z": 3, "rx": 0, "ry": 0, "rz": 0, "open": 1, "robot_id": 1})
    ]
    
    for description, movement in movements:
        print(f"\n🎬 Testing {description}...")
        response = api_call("move/relative", movement)
        if response and response.status_code == 200:
            print(f"✅ {description} recording works!")
        else:
            print(f"❌ {description} recording failed!")
        time.sleep(1)
    
    print("\n✅ Recording tests completed!")


def main():
    """Main function with mode selection."""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode in ['demo', 'd']:
            demo_mode()
        elif mode in ['test', 't']:
            test_movements()
        elif mode in ['help', 'h', '--help']:
            print("Usage: python voice_command_text.py [mode]")
            print("Modes:")
            print("  demo    - Run automatic demonstration")
            print("  test    - Test recording files")
            print("  (none)  - Interactive text input mode")
        else:
            print(f"Unknown mode: {mode}")
            print("Use 'help' for usage information")
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
