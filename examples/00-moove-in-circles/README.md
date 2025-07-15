# PhosphoBot: Move in Circles Example

This example demonstrates how to use the PhosphoBot API to move a robot in circular patterns. The script requires explicit robot selection for safety.

## Prerequisites

- Python 3.6+
- A robot running the PhosphoBot server
- Required Python packages (install via `pip install -r requirements.txt`)

## Usage

### Basic Usage
```bash
# Run with required robot ID (must specify which robot to control)
python circles_absolute.py --robot-id 5A68009540
```

### Advanced Usage
```bash
# Specify a different robot arm by device name
python circles_absolute.py --robot-id 5A68011529

# Customize number of circles and steps
python circles_absolute.py --robot-id 5A68009540 --circles 3 --steps 20

# Combine options
python circles_absolute.py --robot-id 5A68009448 --circles 10 --steps 40
```

### Command Line Options
- `--robot-id` (required): Robot device name to control (e.g., "5A68009540")
- `--circles`: Number of circles to perform (default: 5)  
- `--steps`: Number of steps per circle (default: 30)

### Help
```bash
python circles_absolute.py --help
```

## Configuration

The script `circles_absolute.py` contains several configurable parameters:

```python
# Network Configuration
PI_IP: str = "127.0.0.1"  # IP address of the robot
PI_PORT: int = 80         # Port of the robot's API server

# Default Movement Parameters  
NUMBER_OF_STEPS: int = 30 # Number of steps to complete one circle
NUMBER_OF_CIRCLES: int = 5 # Number of circles to perform
```

Modify these values according to your setup.

## Robot Selection

The script automatically:
1. Queries the PhosphoBot server to get available robots
2. Maps the provided device name to the corresponding robot ID
3. Lists available robots if the specified device name is not found

This ensures you're controlling the intended robot and provides safety through explicit robot selection.

## How to Run

1. Make sure your robot is powered on and the PhosphoBot server is running
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Update the `PI_IP` and `PI_PORT` variables in the script if needed
4. Run the script with the required robot ID:
   ```
   python circles_absolute.py --robot-id <DEVICE_NAME>
   ```

**Note**: The `--robot-id` parameter is required for safety. The script will show available robots if you provide an invalid device name.

## What the Script Does

1. Initializes the robot using the API's `/move/init` endpoint
2. Moves the robot in circular patterns by:
   - Calculating positions using sine and cosine functions
   - Sending absolute position commands to the `/move/absolute` endpoint
   - Creating a circle with a diameter of 4cm
   - Repeating the pattern for the specified number of circles

## Customization

You can modify the script to change:

- The size of the circles by adjusting the multiplier values (currently 4)
- The speed of movement by changing the `time.sleep(0.03)` value
- The number of circles using the `--circles` command line argument
- The smoothness of circles using the `--steps` command line argument

## Technical Details

The script uses absolute positioning with the `/move/absolute` endpoint. Each movement command includes:

- Position coordinates: `x`, `y`, `z` (in centimeters)
- Orientation angles: `rx`, `ry`, `rz` (in degrees)
- Robot ID: Specifies which robot to control in multi-robot setups
- Gripper state: `open` parameter (0 = closed, 1 = open)
