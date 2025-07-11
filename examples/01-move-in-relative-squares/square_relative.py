import time
import requests
import argparse
import sys

# Configurations
PI_IP: str = "127.0.0.1"
PI_PORT: int = 80
NUMBER_OF_SQUARES: int = 100


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
    parser = argparse.ArgumentParser(description='Move robot arm in relative squares')
    parser.add_argument(
        '--robot-id', 
        type=str, 
        required=True,
        help='Robot device name to control (e.g., 5A68009540)'
    )
    parser.add_argument(
        '--squares', 
        type=int, 
        default=NUMBER_OF_SQUARES,
        help=f'Number of squares to perform (default: {NUMBER_OF_SQUARES})'
    )
    
    args = parser.parse_args()
    
    # Get robot_id from device name
    robot_id = get_robot_id_from_device_name(args.robot_id)
    if robot_id is None:
        sys.exit(1)
    
    print(f"🤖 Moving robot arm in relative squares")
    print(f"   Robot device: {args.robot_id} (ID: {robot_id})")
    print(f"   Squares: {args.squares}")
    print()

    # Example code to move the robot in a square of 4 cm x 4 cm
    # 1 - Initialize the robot
    call_to_api("init")
    print("Initializing robot")
    time.sleep(2)

    # We move it to the top left corner of the square
    call_to_api("relative", {"x": 0, "y": -3, "z": 3, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": robot_id})
    print("Moving to top left corner")
    time.sleep(0.2)

    # With the move relative endpoint, we can move relative to its current position
    # 2 - We make the robot follow a 3 cm x 3 cm square
    for square_num in range(args.squares):
        print(f"🔲 Square {square_num + 1}/{args.squares}")
        
        # Move to the top right corner
        call_to_api(
            "relative", {"x": 0, "y": 3, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": robot_id}
        )
        print("Moving to top right corner")
        time.sleep(0.2)

        # Move to the bottom right corner
        call_to_api(
            "relative", {"x": 0, "y": 0, "z": -3, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": robot_id}
        )
        print("Moving to bottom right corner")
        time.sleep(0.2)

        # Move to the bottom left corner
        call_to_api(
            "relative", {"x": 0, "y": -3, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": robot_id}
        )
        print("Moving to bottom left corner")
        time.sleep(0.2)

        # Move to the top left corner
        call_to_api(
            "relative", {"x": 0, "y": 0, "z": 3, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": robot_id}
        )
        print("Moving to top left corner")
        time.sleep(0.2)
    
    print(f"✅ Completed {args.squares} squares successfully!")


if __name__ == "__main__":
    main()
