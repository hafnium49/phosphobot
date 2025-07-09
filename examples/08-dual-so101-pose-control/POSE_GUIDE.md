# SO-101 Dual Arm Pose Specification Guide

This guide explains how to specify poses (position + orientation) for SO-101 robotic arms in the phosphobot system.

## 📐 Coordinate System

### Base Reference Frame
The SO-101 arms use a standard robotics coordinate system with the origin at the robot base:

```
        Z (up)
        |
        |
        |________Y (left)
       /
      /
     X (forward)
```

### Position Coordinates
```python
position = [x, y, z]  # Units: meters
```

- **X-axis**: Forward/backward movement
  - `+X`: Forward (away from robot base)
  - `-X`: Backward (toward robot base)
  - Typical range: `0.10` to `0.40` meters

- **Y-axis**: Left/right movement  
  - `+Y`: Left (from robot's perspective)
  - `-Y`: Right (from robot's perspective)
  - Typical range: `-0.30` to `+0.30` meters

- **Z-axis**: Up/down movement
  - `+Z`: Up (away from table surface)
  - `-Z`: Down (toward table surface)
  - Typical range: `0.05` to `0.35` meters

### Orientation (Euler Angles)
```python
orientation = [rx, ry, rz]  # Units: degrees
```

- **rx (Roll)**: Rotation around X-axis (forward/back)
  - `+rx`: Clockwise rotation when looking forward
  - `-rx`: Counter-clockwise rotation when looking forward
  - Range: `-180°` to `+180°`

- **ry (Pitch)**: Rotation around Y-axis (left/right)
  - `+ry`: Gripper points down
  - `-ry`: Gripper points up
  - Range: `-90°` to `+90°`

- **rz (Yaw)**: Rotation around Z-axis (up/down)
  - `+rz`: Gripper rotates counter-clockwise (viewed from above)
  - `-rz`: Gripper rotates clockwise (viewed from above)
  - Range: `-180°` to `+180°`

## 🎯 Common Pose Examples

### Safe Positions
```python
# Safe parking positions (arms spread apart)
safe_left = {
    'position': [0.25, 0.15, 0.25],    # Forward, right, high
    'orientation': [0, 0, 0]            # Neutral orientation
}

safe_right = {
    'position': [0.25, -0.15, 0.25],   # Forward, left, high  
    'orientation': [0, 0, 0]            # Neutral orientation
}
```

### Home Positions
```python
# Ready positions for work
home_left = {
    'position': [0.20, 0.10, 0.18],    # Close, slightly right, medium height
    'orientation': [0, 0, -15]          # Slightly angled inward
}

home_right = {
    'position': [0.20, -0.10, 0.18],   # Close, slightly left, medium height
    'orientation': [0, 0, 15]           # Slightly angled inward
}
```

### Pickup Positions
```python
# Positions for picking up objects
pickup_left = {
    'position': [0.30, 0.12, 0.12],    # Extended forward, low
    'orientation': [0, 45, 0]           # Angled down for pickup
}

pickup_right = {
    'position': [0.30, -0.12, 0.12],   # Extended forward, low
    'orientation': [0, 45, 0]           # Angled down for pickup
}
```

### Handoff Positions
```python
# Positions for object transfer between arms
handoff_left = {
    'position': [0.20, 0.05, 0.18],    # Close to center
    'orientation': [0, 0, 45]           # Angled toward right arm
}

handoff_right = {
    'position': [0.20, -0.05, 0.18],   # Close to center
    'orientation': [0, 0, -45]          # Angled toward left arm
}
```

## 🔧 Programming Examples

### Absolute Pose Control
```python
from dual_so101_controller import DualSO101Controller

controller = DualSO101Controller()

# Move left arm to specific pose
controller.move_arm_absolute_pose(
    robot_id=0,                        # Left arm
    position=[0.25, 0.15, 0.20],      # 25cm forward, 15cm right, 20cm up
    orientation=[0, 30, -20],          # 30° pitch down, 20° yaw left
    position_tolerance=0.01,           # 1cm tolerance
    orientation_tolerance=5.0          # 5° tolerance
)
```

### Relative Pose Adjustments
```python
# Move arm relative to current position
controller.move_arm_relative_pose(
    robot_id=0,                        # Left arm
    delta_position=[2, 0, -1],        # 2cm forward, 1cm down (in cm)
    delta_orientation=[0, 5, 0],       # 5° more pitch down (in degrees)
    gripper_open=1.0                   # Open gripper
)
```

### Synchronized Dual-Arm Movement
```python
from dual_arm_coordination import DualArmCoordinator

coordinator = DualArmCoordinator(controller)

# Move both arms simultaneously
coordinator.synchronized_movement(
    left_pose=[0.25, 0.15, 0.20],     # Left arm target
    right_pose=[0.25, -0.15, 0.20],   # Right arm target
    left_orientation=[0, 0, -15],      # Left arm orientation
    right_orientation=[0, 0, 15]       # Right arm orientation
)
```

## ⚠️ Safety Considerations

### Workspace Limits
- **X-axis**: Stay within `0.10m` to `0.40m` to avoid collisions
- **Y-axis**: Keep arms separated by at least `0.20m` (`±0.10m` from center)
- **Z-axis**: Minimum height `0.05m` to avoid table collision

### Orientation Limits
- **Pitch (ry)**: Avoid extreme angles beyond `±60°`
- **Roll/Yaw**: Generally keep within `±45°` for most tasks

### Collision Avoidance
```python
# Example: Check if poses are safe before moving
def is_pose_safe(position, orientation):
    x, y, z = position
    rx, ry, rz = orientation
    
    # Check workspace bounds
    if not (0.10 <= x <= 0.40):
        return False, "X position out of bounds"
    if not (-0.30 <= y <= 0.30):
        return False, "Y position out of bounds"  
    if not (0.05 <= z <= 0.35):
        return False, "Z position out of bounds"
    
    # Check orientation limits
    if abs(ry) > 60:
        return False, "Pitch angle too extreme"
    
    return True, "Pose is safe"

# Usage
pose_ok, message = is_pose_safe([0.25, 0.15, 0.20], [0, 30, -15])
if pose_ok:
    controller.move_arm_absolute_pose(robot_id=0, position=[0.25, 0.15, 0.20])
else:
    print(f"Unsafe pose: {message}")
```

## 🎮 Testing Your Poses

### Interactive Testing
Use the interactive control script to test poses manually:
```bash
python interactive_control.py
```

### Gradual Movement
Start with small movements and gradually increase:
```python
# Start from safe position
controller.move_arm_absolute_pose(robot_id=0, position=[0.25, 0.15, 0.25])

# Make small adjustments
controller.move_arm_relative_pose(robot_id=0, delta_position=[1, 0, 0])  # 1cm forward
controller.move_arm_relative_pose(robot_id=0, delta_position=[0, 1, 0])  # 1cm left
controller.move_arm_relative_pose(robot_id=0, delta_position=[0, 0, -1]) # 1cm down
```

## 📊 Pose Validation

### Real-time Pose Monitoring
```python
# Get current pose
current_pose = controller.get_current_pose(robot_id=0)
print(f"Current position: {current_pose}")

# Verify pose after movement
target_position = [0.25, 0.15, 0.20]
controller.move_arm_absolute_pose(robot_id=0, position=target_position)

actual_pose = controller.get_current_pose(robot_id=0)
position_error = np.linalg.norm(np.array(actual_pose['position']) - np.array(target_position))
print(f"Position error: {position_error:.3f}m")
```

This comprehensive guide should help you specify precise poses for your dual SO-101 robotic arms!
