# PhosphoBot: Move in Relative Squares Example

This example demonstrates how to use the PhosphoBot API to move a robot in square patterns using relative positioning. The script supports command line arguments for robot selection and customization.

## Prerequisites

- Python 3.6+
- A robot running the PhosphoBot server
- Required Python packages (install via `pip install -r requirements.txt`)

## Configuration

The script `square_relative.py` contains several configurable parameters:

```python
# Configurations
PI_IP: str = "127.0.0.1"  # IP address of the robot
PI_PORT: int = 80         # Port of the robot's API server
NUMBER_OF_SQUARES: int = 100 # Default number of squares to perform
```

Modify these values according to your setup.

## How to Run

1. Make sure your robot is powered on and the PhosphoBot server is running
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Update the `PI_IP` and `PI_PORT` variables in the script if needed
4. Run the script with the required robot ID:
   ```
   python square_relative.py --robot-id <DEVICE_NAME>
   ```

## Command Line Arguments

The script supports the following command line arguments:

- `--robot-id` (required): Robot device name to control (e.g., "5A68009540")
- `--squares` (optional): Number of squares to perform (default: 100)

### Examples

```bash
# Basic usage with robot selection
python square_relative.py --robot-id 5A68009540

# Perform only 5 squares
python square_relative.py --robot-id 5A68009540 --squares 5

# Show help
python square_relative.py --help
```

## Robot Selection

The script automatically:
1. Queries the PhosphoBot server to get available robots
2. Maps the provided device name to the corresponding robot ID
3. Lists available robots if the specified device name is not found

This ensures you're controlling the intended robot and provides safety through explicit robot selection.

## What the Script Does

1. Initializes the robot using the API's `/move/init` endpoint
2. Moves the robot to the top left corner of the square
3. Makes the robot follow a 3cm x 3cm square pattern by:
   - Moving to the top right corner
   - Moving to the bottom right corner
   - Moving to the bottom left corner
   - Moving back to the top left corner
   - Repeating this pattern for the specified number of squares

## Customization

You can modify the script to change:

- The size of the squares by adjusting the values in the position parameters (currently 3cm)
- The speed of movement by changing the `time.sleep(0.2)` value
- The number of square patterns using the `--squares` command line argument
- The movement pattern by modifying the sequence of relative movements

## Technical Details

The script uses relative positioning with the `/move/relative` endpoint, which moves the robot relative to its current position. Each movement command includes:

- Position deltas: `x`, `y`, `z` (in centimeters)
- Orientation deltas: `rx`, `ry`, `rz` (in degrees)
- Robot ID: Specifies which robot to control in multi-robot setups
- Gripper state: `open` parameter (0 = closed, 1 = open)
