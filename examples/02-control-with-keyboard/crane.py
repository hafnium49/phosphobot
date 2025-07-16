#!/usr/bin/env python3

"""
This script let's you control your robot using keyboard inputs.
The robot arm is controlled using the following keys:
- Arrow Up:    Move forward (increase Y)
- Arrow Down:  Move backward (decrease Y)
- Arrow Right: Move right (increase X)
- Arrow Left:  Move left (decrease X)
- A:           Move up (increase Z)
- D:           Move down (decrease Z)
- Space:       Toggle open state
- J:           Read joint positions

Usage:
  python crane.py                         # Control left arm (ID 3), no init
  python crane.py --robot-id 2            # Control right arm (ID 2), no init
  python crane.py --init                  # Control left arm with initialization
  python crane.py --robot-id 2 --init     # Control right arm with initialization
  python crane.py --alternative           # Use alternative keyboard control
  python crane.py --help                  # Show all options
"""

import requests
import time
import logging
from typing import cast
from pynput.keyboard import KeyCode
from typing import Dict, Literal, Set, Tuple
from pynput import keyboard as pynput_keyboard
import threading
import sys
import select
import termios
import tty


# Configuration
BASE_URL: str = "http://127.0.0.1:80/"
# ROBOT_ID will be set from command line argument in main()
ROBOT_ID: int = 3  # Default left arm ID (3 = 5A68011258, 2 = 5A68009540)
STEP_SIZE: int = 2  # Movement step in centimeters
SLEEP_TIME: float = 0.05  # Loop sleep time (20 Hz)

# Global open state (initially 1 as set in init_robot)
open_state: Literal[0, 1] = 1


def behind_or_front() -> Literal["Behind", "Facing"]:
    """
    Returns the relative position of the user to the robot.
    """
    # Auto-select "Behind" for automated execution
    print("Auto-selecting 'Behind' position for robot control")
    return "Behind"


user_position: Literal["Behind", "Facing"] = behind_or_front()

# Key mappings for alphanumeric keys (z-axis movement - up/down)
KEY_MAPPINGS: Dict[str, Tuple[int, int, int]] = {
    "a": (0, 0, STEP_SIZE),  # Increase Z (move up)
    "d": (0, 0, -STEP_SIZE),  # Decrease Z (move down)
}

# Special function keys
FUNCTION_KEYS = {
    "j": "read_joints",  # Read joint positions
}

# Key mappings for special keys (arrow keys for x and y axes)
# The direction of movement is reversed if the user is facing the robot.
SPECIAL_KEY_MAPPINGS: Dict[KeyCode | str, Tuple[int, int, int]] = (
    {
        pynput_keyboard.Key.up: (0, STEP_SIZE, 0),  # Increase Y (move forward)
        pynput_keyboard.Key.down: (0, -STEP_SIZE, 0),  # Decrease Y (move backward)
        pynput_keyboard.Key.right: (STEP_SIZE, 0, 0),  # Increase X (move right)
        pynput_keyboard.Key.left: (-STEP_SIZE, 0, 0),  # Decrease X (move left)
    }
    if user_position == "Behind"
    else {
        pynput_keyboard.Key.up: (0, -STEP_SIZE, 0),  # Decrease Y (move forward when facing)
        pynput_keyboard.Key.down: (0, STEP_SIZE, 0),  # Increase Y (move backward when facing)
        pynput_keyboard.Key.right: (STEP_SIZE, 0, 0),  # Increase X (move right)
        pynput_keyboard.Key.left: (-STEP_SIZE, 0, 0),  # Decrease X (move left)
    }
)

# Set to track currently pressed keys (both string and special keys)
keys_pressed: Set[KeyCode | str] = set()


def toggle_open_state() -> None:
    """Toggle the open state and send a relative move command with no displacement."""
    global open_state
    open_state = 0 if open_state == 1 else 1
    data: Dict[str, float] = {
        "x": 0,
        "y": 0,
        "z": 0,
        "rx": 0,
        "ry": 0,
        "rz": 0,
        "open": open_state,
    }
    try:
        response = requests.post(f"{BASE_URL}move/relative?robot_id={ROBOT_ID}", json=data, timeout=1)
        response.raise_for_status()
        logging.info(f"Toggled open state to {open_state}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to toggle open state: {e}")


def on_press(key: KeyCode | str) -> None:
    # Handle space key separately to toggle open state immediately.
    if key == pynput_keyboard.Key.space:
        toggle_open_state()
        return
    # Handle alphanumeric keys (e.g. "a", "d")
    try:
        char = key.char.lower()  # type: ignore
        # Check if it's a function key
        if char in FUNCTION_KEYS:
            if FUNCTION_KEYS[char] == "read_joints":
                display_joint_positions()
        elif char in KEY_MAPPINGS:
            keys_pressed.add(char)
            logging.debug(f"Key pressed: {char}")
    except AttributeError:
        # Handle special keys (e.g. arrow keys)
        if key in SPECIAL_KEY_MAPPINGS:
            keys_pressed.add(key)
            logging.debug(f"Special key pressed: {key}")
    except Exception as e:
        logging.warning(f"Error handling key press: {e}")


def on_release(key: KeyCode | str) -> None:
    # Remove keys from the pressed set when released.
    try:
        char = key.char.lower()  # type: ignore
        keys_pressed.discard(char)
        logging.debug(f"Key released: {char}")
    except AttributeError:
        if key in SPECIAL_KEY_MAPPINGS:
            keys_pressed.discard(key)
            logging.debug(f"Special key released: {key}")
    except Exception as e:
        logging.warning(f"Error handling key release: {e}")


def init_robot() -> None:
    """Initialize the robot by calling /move/init and setting an absolute starting position."""
    endpoint_init = f"{BASE_URL}move/init?robot_id={ROBOT_ID}"
    endpoint_absolute = f"{BASE_URL}move/absolute?robot_id={ROBOT_ID}"
    
    # Determine robot arm name for logging
    arm_name = "Left Arm" if ROBOT_ID == 3 else "Right Arm" if ROBOT_ID == 2 else f"Arm {ROBOT_ID}"
    
    try:
        logging.info(f"Initializing {arm_name} (Robot ID {ROBOT_ID})...")
        response = requests.post(endpoint_init, json={}, timeout=5)
        response.raise_for_status()
        time.sleep(2)
        
        logging.info("Setting robot to starting position...")
        response = requests.post(
            endpoint_absolute,
            json={"x": 0, "y": 0, "z": 0, "rx": 1.5, "ry": 0, "rz": 0, "open": 1},
            timeout=5,
        )
        response.raise_for_status()
        logging.info(f"{arm_name} (Robot ID {ROBOT_ID}) initialized successfully")
        
        # Only display joint positions if explicitly requested
        # User can press 'J' key to read joint positions anytime
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to initialize {arm_name} (Robot ID {ROBOT_ID}): {e}")
    time.sleep(1)  # Allow time for the robot to initialize


def control_robot():
    """Control the robot with keyboard inputs using /move/relative."""
    endpoint = f"{BASE_URL}move/relative?robot_id={ROBOT_ID}"
    
    # Determine robot arm name for logging
    arm_name = "Left Arm" if ROBOT_ID == 3 else "Right Arm" if ROBOT_ID == 2 else f"Arm {ROBOT_ID}"

    logging.info(f"Controlling {arm_name} (Robot ID {ROBOT_ID}) with keyboard:")
    logging.info("  Arrow Up:    Move forward (increase Y)")
    logging.info("  Arrow Down:  Move backward (decrease Y)")
    logging.info("  Arrow Right: Move right (increase X)")
    logging.info("  Arrow Left:  Move left (decrease X)")
    logging.info("  A:           Move up (increase Z)")
    logging.info("  D:           Move down (decrease Z)")
    logging.info("  Space:       Toggle gripper open/close")
    logging.info("  J:           Read current joint positions")
    logging.info("Press Ctrl+C to exit")
    logging.info("Make sure this terminal window has focus to capture keyboard input!")

    # Start the pynput keyboard listener.
    listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # Test if listener is working
    logging.info("Keyboard listener started. Testing keyboard input...")
    logging.info("Try pressing any key to test keyboard detection...")
    
    # Wait a moment for the listener to initialize
    time.sleep(0.5)

    try:
        loop_count = 0
        while True:
            # Reset movement deltas.
            delta_x, delta_y, delta_z = 0.0, 0.0, 0.0

            # Aggregate movement contributions from pressed keys.
            for key in keys_pressed:
                if isinstance(key, str):  # Alphanumeric keys.
                    dx, dy, dz = KEY_MAPPINGS.get(key, (0, 0, 0))
                else:  # Special keys (arrow keys).
                    dx, dy, dz = SPECIAL_KEY_MAPPINGS.get(key, (0, 0, 0))
                delta_x += dx
                delta_y += dy
                delta_z += dz

            global open_state
            # Send a relative move command if any movement key is pressed.
            if delta_x or delta_y or delta_z:
                data = {
                    "x": delta_x,
                    "y": delta_y,
                    "z": delta_z,
                    "rx": 0,
                    "ry": 0,
                    "rz": 0,
                    "open": open_state,
                }
                try:
                    response = requests.post(endpoint, json=data, timeout=1)
                    response.raise_for_status()
                    logging.info(
                        f"Sent movement: x={delta_x}, y={delta_y}, z={delta_z}"
                    )
                except requests.exceptions.RequestException as e:
                    logging.error(f"Request failed: {e}")
            
            # Show a periodic status message to indicate the program is running
            loop_count += 1
            if loop_count % 1000 == 0:  # Every 50 seconds (1000 * 0.05)
                logging.info(f"Keyboard controller running... (make sure this window has focus)")

            time.sleep(SLEEP_TIME)
    except KeyboardInterrupt:
        logging.info("Exiting...")
    finally:
        listener.stop()


def test_keyboard_input():
    """Test function to verify keyboard input is working."""
    logging.info("Testing keyboard input for 5 seconds...")
    logging.info("Press any key during this test...")
    
    test_keys_pressed = set()
    
    def test_on_press(key):
        test_keys_pressed.add(str(key))
        logging.info(f"Test detected key press: {key}")
    
    def test_on_release(key):
        test_keys_pressed.discard(str(key))
        logging.info(f"Test detected key release: {key}")
    
    listener = pynput_keyboard.Listener(on_press=test_on_press, on_release=test_on_release)
    listener.start()
    
    try:
        time.sleep(5)
        if test_keys_pressed or len(test_keys_pressed) > 0:
            logging.info("Keyboard test passed!")
        else:
            logging.warning("No keyboard input detected during test. Check terminal focus.")
    finally:
        listener.stop()


# Add a fallback keyboard method
def get_char():
    """Get a single character from stdin without pressing Enter (Unix/Linux only)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def alternative_keyboard_control():
    """Alternative keyboard control using standard input."""
    logging.info("Using alternative keyboard input method...")
    logging.info("Controls: w=forward, s=backward, a=up, d=down, q=left, e=right, j=read joints, space=toggle gripper, x=quit")
    
    try:
        while True:
            char = get_char().lower()
            
            if char == 'x':
                logging.info("Quitting...")
                break
            elif char == ' ':
                toggle_open_state()
            elif char == 'j':
                display_joint_positions()
            elif char in ['w', 's', 'a', 'd', 'q', 'e']:
                # Map characters to movements
                delta_x, delta_y, delta_z = 0, 0, 0
                if char == 'w':  # forward
                    delta_y = STEP_SIZE
                elif char == 's':  # backward
                    delta_y = -STEP_SIZE
                elif char == 'a':  # up
                    delta_z = STEP_SIZE
                elif char == 'd':  # down
                    delta_z = -STEP_SIZE
                elif char == 'q':  # left
                    delta_x = -STEP_SIZE
                elif char == 'e':  # right
                    delta_x = STEP_SIZE
                
                # Send movement command
                endpoint = f"{BASE_URL}move/relative?robot_id={ROBOT_ID}"
                data = {
                    "x": delta_x,
                    "y": delta_y,
                    "z": delta_z,
                    "rx": 0,
                    "ry": 0,
                    "rz": 0,
                    "open": open_state,
                }
                try:
                    response = requests.post(endpoint, json=data, timeout=1)
                    response.raise_for_status()
                    logging.info(f"Sent movement: x={delta_x}, y={delta_y}, z={delta_z}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Request failed: {e}")
                    
    except KeyboardInterrupt:
        logging.info("Exiting alternative control...")
    except Exception as e:
        logging.error(f"Alternative keyboard control failed: {e}")


def read_joint_positions(unit: str = "rad", joints_ids: list = None) -> dict:
    """
    Read the current positions of the robot's joints.
    
    Args:
        unit: The unit of the angles ('rad', 'degrees', 'motor_units')
        joints_ids: List of joint IDs to read. If None, read all joints.
    
    Returns:
        Dictionary containing angles and unit information
    """
    endpoint = f"{BASE_URL}joints/read?robot_id={ROBOT_ID}"
    
    data = {
        "unit": unit
    }
    
    if joints_ids is not None:
        data["joints_ids"] = joints_ids
    
    try:
        response = requests.post(endpoint, json=data, timeout=5)
        response.raise_for_status()
        joint_data = response.json()
        logging.info(f"Joint positions ({unit}): {joint_data['angles']}")
        return joint_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to read joint positions: {e}")
        return {"angles": [], "unit": unit}


def display_joint_positions():
    """Display current joint positions in a readable format."""
    try:
        # Read joint positions in radians
        joint_data_rad = read_joint_positions("rad")
        
        # Read joint positions in degrees for easier interpretation
        joint_data_deg = read_joint_positions("degrees")
        
        print("\n" + "="*50)
        print("CURRENT JOINT POSITIONS")
        print("="*50)
        
        if joint_data_rad["angles"]:
            print("Radians:")
            for i, angle in enumerate(joint_data_rad["angles"]):
                if angle is not None:
                    print(f"  Joint {i+1}: {angle:.4f} rad")
                else:
                    print(f"  Joint {i+1}: Not available")
        
        if joint_data_deg["angles"]:
            print("\nDegrees:")
            for i, angle in enumerate(joint_data_deg["angles"]):
                if angle is not None:
                    print(f"  Joint {i+1}: {angle:.2f}°")
                else:
                    print(f"  Joint {i+1}: Not available")
        
        print("="*50 + "\n")
        
        return joint_data_rad
    except Exception as e:
        logging.error(f"Error displaying joint positions: {e}")
        return None


def main():
    # Configure logging with DEBUG level to see key press events
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Parse command line arguments
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Control robot arm with keyboard')
    parser.add_argument('--robot-id', type=int, default=3, 
                       help='Robot arm ID (default: 3 for left arm, 2 for right arm)')
    parser.add_argument('--alternative', action='store_true',
                       help='Use alternative keyboard control method')
    parser.add_argument('--init', action='store_true',
                       help='Initialize robot before starting control')
    parser.add_argument('--no-init', action='store_true',
                       help='Skip robot initialization (default behavior)')
    
    args = parser.parse_args()
    
    # Set global ROBOT_ID from command line argument
    global ROBOT_ID
    ROBOT_ID = args.robot_id
    
    # Determine robot arm name for logging
    arm_name = "Left Arm" if ROBOT_ID == 3 else "Right Arm" if ROBOT_ID == 2 else f"Arm {ROBOT_ID}"
    
    logging.info(f"Starting crane control for {arm_name} (Robot ID {ROBOT_ID})")
    
    # Check for command line arguments
    force_alternative = args.alternative
    force_init = args.init
    skip_init = args.no_init
    
    # By default, skip initialization unless explicitly requested
    should_init = force_init and not skip_init
    
    if force_alternative:
        logging.info("Using alternative keyboard control mode")
        if should_init:
            logging.info("Initializing robot as requested...")
            init_robot()
        else:
            logging.info("Skipping robot initialization (use --init to force initialization)")
        alternative_keyboard_control()
        return
    
    # Test keyboard input first (only for standard mode)
    test_keyboard_input()
    
    # Initialize robot only if requested
    if should_init:
        logging.info("Initializing robot as requested...")
        init_robot()
    else:
        logging.info("Skipping robot initialization (use --init to force initialization)")
        logging.info("Robot should already be initialized and ready for control")
    
    # Auto-start with standard keyboard control
    logging.info("Auto-starting with standard pynput keyboard control")
    logging.info("Usage options:")
    logging.info("  python crane.py                         # Standard control, robot ID 3, no init")
    logging.info("  python crane.py --robot-id 2            # Standard control, robot ID 2, no init")
    logging.info("  python crane.py --init                  # Standard control, robot ID 3, with init")
    logging.info("  python crane.py --alternative           # Alternative control, robot ID 3, no init")
    logging.info("  python crane.py --robot-id 2 --init     # Standard control, robot ID 2, with init")
    
    try:
        control_robot()
    except Exception as e:
        logging.error(f"Error with standard control: {e}")
        logging.info("Falling back to alternative keyboard control...")
        alternative_keyboard_control()


if __name__ == "__main__":
    main()