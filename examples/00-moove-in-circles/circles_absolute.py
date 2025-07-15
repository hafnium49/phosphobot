import math
import time
import requests
import argparse
import sys

# Configurations
PI_IP: str = "127.0.0.1"
PI_PORT: int = 80
NUMBER_OF_STEPS: int = 30
NUMBER_OF_CIRCLES: int = 5


# Function to call the API
def call_to_api(endpoint: str, data: dict = {}):
    response = requests.post(f"http://{PI_IP}:{PI_PORT}/move/{endpoint}", json=data)
    return response.json()


def get_robot_id_from_device_name(device_name: str):
    """
    Get robot_id (index) from device name by checking server status.
    """
    try:
        response = requests.get(f"http://{PI_IP}:{PI_PORT}/status")
        status = response.json()
        
        # Find the robot with matching device name
        for i, robot_status in enumerate(status.get('robot_status', [])):
            if robot_status.get('device_name') == device_name:
                return i
        
        # If not found, list available robots
        print(f"❌ Robot with device name '{device_name}' not found!")
        print("Available robots:")
        for i, robot_status in enumerate(status.get('robot_status', [])):
            print(f"  Robot {i}: {robot_status.get('device_name')}")
        return None
        
    except Exception as e:
        print(f"❌ Failed to get robot status: {e}")
        return None


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Move robot arm in circles')
    parser.add_argument(
        '--robot-id', 
        type=str, 
        required=True,
        help='Robot device name to control (e.g., 5A68009540)'
    )
    parser.add_argument(
        '--circles', 
        type=int, 
        default=NUMBER_OF_CIRCLES,
        help=f'Number of circles to perform (default: {NUMBER_OF_CIRCLES})'
    )
    parser.add_argument(
        '--steps', 
        type=int, 
        default=NUMBER_OF_STEPS,
        help=f'Number of steps per circle (default: {NUMBER_OF_STEPS})'
    )
    
    args = parser.parse_args()
    
    # Get robot_id from device name
    robot_id = get_robot_id_from_device_name(args.robot_id)
    if robot_id is None:
        sys.exit(1)
    
    print(f"🤖 Moving robot arm in circles")
    print(f"   Robot device: {args.robot_id} (ID: {robot_id})")
    print(f"   Circles: {args.circles}")
    print(f"   Steps per circle: {args.steps}")
    print()

    # Example code to move the robot in a circle
    # 1 - Initialize the robot
    call_to_api("init")
    print("Initializing robot")
    time.sleep(2)

    # With the move absolute endpoint, we can move the robot in an absolute position
    # 2 - We move the robot in a circle with a diameter of 4 cm
    for circle in range(args.circles):
        print(f"🔄 Circle {circle + 1}/{args.circles}")
        for step in range(args.steps):
            position_y: float = 4 * math.sin(2 * math.pi * step / args.steps)
            position_z: float = 4 * math.cos(2 * math.pi * step / args.steps)
            call_to_api(
                "absolute",
                {
                    "x": 0,
                    "y": 0,
                    "z": position_z,
                    "rx": 0,
                    "ry": 0,
                    # rz is used to move the robot from left to right
                    "rz": position_y,
                    "open": 0,
                    "robot_id": robot_id,  # Add robot_id to specify which arm to control
                },
            )
            print(f"Step {step} - x: 0, y: {position_y:.3f}, z: {position_z:.3f}")
            time.sleep(0.03)
    
    print(f"✅ Completed {args.circles} circles successfully!")


if __name__ == "__main__":
    main()
