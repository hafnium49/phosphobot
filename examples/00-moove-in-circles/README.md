# PhosphoBot: Move in Circles Example

This example demonstrates how to use the PhosphoBot API to move a robot in circular patterns.

## Prerequisites

- Python 3.6+
- A robot running the PhosphoBot server
- Required Python packages (install via `pip install -r requirements.txt`)

## Usage

### Basic Usage
```bash
# Run with default settings (robot device: 5A68009540, 5 circles, 30 steps)
python circles_absolute.py
```

### Advanced Usage
```bash
# Specify a different robot arm by device name
python circles_absolute.py --robot-id 5A68011529

# Customize number of circles and steps
python circles_absolute.py --circles 3 --steps 20

# Combine options
python circles_absolute.py --robot-id 5A68009448 --circles 10 --steps 40
```

### Command Line Options
- `--robot-id`: Robot device name to control (default: 5A68009540)
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
DEFAULT_ROBOT_ID: str = "5A68009540"  # Default robot device name
```

Modify these values according to your setup.

## How to Run

1. Make sure your robot is powered on and the PhosphoBot server is running
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Update the `PI_IP` and `PI_PORT` variables in the script if needed
4. Run the script:
   ```
   python circles_absolute.py
   ```

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
- The number of circles with the `NUMBER_OF_CIRCLES` parameter
- The smoothness of circles by adjusting `NUMBER_OF_STEPS`
