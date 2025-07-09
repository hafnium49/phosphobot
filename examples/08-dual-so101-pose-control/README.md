# Dual SO-101 Pose Control

This example demonstrates how to control a pair of SO-101 robotic arms using direct pose commands (position + orientation) instead of AI control.

## Prerequisites

- Two SO-101 robotic arms connected to your computer
- Phosphobot server running (`phosphobot run`)
- Python 3.10+

## What this example does

1. **Direct Pose Control**: Move arms to specific 3D positions and orientations
2. **Dual Arm Coordination**: Synchronize movements between two arms
3. **Gripper Control**: Open and close grippers independently
4. **Relative Movements**: Make incremental adjustments to current poses

## Hardware Setup

1. Connect both SO-101 arms to your computer via USB
2. Make sure both arms are detected by the phosphobot server
3. Arms will be assigned robot IDs: 0 (first) and 1 (second)

## Installation

```bash
# Install required dependencies
pip install httpx numpy

# Or if using the script requirements
pip install -r requirements.txt
```

## Usage

### Basic Example
```bash
python dual_arm_basic.py
```

### Advanced Coordination
```bash
python dual_arm_coordination.py
```

### Interactive Control
```bash
python interactive_control.py
```

## Key Concepts

### Coordinate System
- **X-axis**: Forward/backward (positive = forward)
- **Y-axis**: Left/right (positive = left)  
- **Z-axis**: Up/down (positive = up)
- **Orientations**: Euler angles in degrees (rx, ry, rz)

### Units
- **Absolute positions**: Meters
- **Relative positions**: Centimeters
- **Orientations**: Degrees
- **Gripper**: 0.0 = closed, 1.0 = open

### Safety Notes
- Start with small movements to test your setup
- Keep emergency stop accessible
- Ensure adequate workspace for both arms
- Test single arm movements before dual arm coordination
- **Use workspace validation** to avoid forbidden poses

### Workspace Validation
This package includes tools to check if poses are reachable and safe:

```bash
# Quick demo of workspace validation
python workspace_demo.py

# Check if a specific pose is reachable
python workspace_validator.py --check-pose 0.25 0.15 0.20

# Get workspace summary and boundaries  
python workspace_validator.py --summary

# Sample and visualize the workspace
python workspace_validator.py --sample-workspace --resolution 15
python workspace_validator.py --visualize
```

**Safe workspace bounds for SO-101:**
- X (forward): 0.08m to 0.35m
- Y (lateral): ±0.25m  
- Z (height): 0.03m to 0.32m
- Orientations: ±90° roll/pitch, ±180° yaw

**Always validate poses** before sending to the robot to avoid:
- Base collisions
- Ground collisions  
- Joint limit violations
- Unreachable positions

## Troubleshooting

### Arms not detected
1. Check USB connections
2. Restart phosphobot server: `phosphobot run`
3. Verify robot IDs in the web dashboard at `localhost:80`

### Movement errors
1. Check if arms are in a safe starting position
2. Reduce movement distances
3. Ensure target positions are within arm reach

### Connection issues
1. Verify phosphobot server is running on `localhost:80`
2. Check firewall settings
3. Try restarting the server

## Contributing

Feel free to extend these examples with:
- More complex dual-arm tasks
- Different coordination patterns
- Safety features
- Vision-guided movements
