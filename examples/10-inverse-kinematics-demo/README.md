# SO-101 Inverse Kinematics Demo

## Summary

This example demonstrates how to use inverse kinematics (IK) with the **SO-101 5-DOF robotic arm** for precise end effector control. Learn how the robot automatically calculates joint angles to achieve desired end effector poses.

## Quick Start: Running the Demo

```bash
# Run the interactive inverse kinematics demonstration
python inverse_kinematics_demo.py
```

## Understanding Inverse Kinematics

**Inverse Kinematics (IK)** solves the problem: *"Given a desired end effector pose, what joint angles are needed?"*

**Forward Kinematics (FK)** solves the reverse: *"Given joint angles, where is the end effector?"*

### Why IK is Important
- **Intuitive Control**: Think in terms of where you want the gripper, not joint angles
- **Automatic Calculation**: Robot computes complex trigonometry for you  
- **Precision**: Achieve exact positioning with sub-millimeter accuracy
- **Safety**: Built-in workspace and joint limit checking

## Basic IK Usage

### Simple End Effector Movement
```python
from dual_so101_controller import DualSO101Controller

# Initialize controller
controller = DualSO101Controller()

# Move end effector to specific position - IK automatically calculates joint angles
controller.move_arm_absolute_pose(
    robot_id=0,
    position=[0.25, 0.15, 0.20],  # x, y, z in meters
    orientation=[0, 45, -15]       # roll, pitch, yaw in degrees
)

# IK happens automatically - you don't see the joint angle calculations!
controller.close()
```

### Getting Current End Effector Pose
```python
# Use forward kinematics to get current pose
current_pose = controller.get_current_pose(robot_id=0)
print(f"Current end effector position: {current_pose}")
```

## IK vs Direct Joint Control

| Method | Complexity | Use Case |
|--------|------------|----------|
| **IK Control** ✅ | Easy | "Move gripper to this position" |
| **Joint Control** ❌ | Hard | "Set joint 1 to 45°, joint 2 to..." |

### IK Control (Recommended)
```python
# Easy: Think about end effector position
target_position = [0.30, 0.10, 0.15]  # Where you want the gripper
controller.move_arm_absolute_pose(robot_id=0, position=target_position)
```

### Joint Control (Complex)
```python
# Hard: Must manually calculate what joint angles achieve the desired pose
joint_angles = [30, 45, -60, 90, 15]  # Degrees - where does this put the gripper?
# ❌ Very difficult to visualize final position
# ❌ Requires complex trigonometry calculations
# ❌ Trial and error to get desired pose
```

## Advanced IK Features

### Precision Control
```python
# High precision movement
controller.move_arm_absolute_pose(
    robot_id=0,
    position=[0.25, 0.15, 0.20],
    orientation=[0, 30, 0],
    position_tolerance=0.002,      # 2mm precision
    orientation_tolerance=2.0,     # 2° precision
    max_trials=5                   # Multiple attempts for difficult poses
)
```

### Multiple Solutions
```python
# Same end effector pose can be achieved with different orientations
target_pos = [0.25, 0.15, 0.18]

# Different approaches to same position
orientations = [
    [0, 0, 0],      # Horizontal gripper
    [0, 30, 0],     # Tilted down 30°
    [0, 0, 45],     # Rotated 45°
]

for orientation in orientations:
    controller.move_arm_absolute_pose(
        robot_id=0, 
        position=target_pos, 
        orientation=orientation
    )
    # Same position, different joint configurations!
```

## Understanding IK Challenges

### Workspace Limits
Not all positions are reachable - IK will fail for poses outside the robot's workspace:

```python
# These poses may cause IK to fail
unreachable_poses = [
    [0.50, 0.30, 0.10],  # Too far away
    [0.05, 0.00, 0.05],  # Too close to base  
    [0.25, 0.35, 0.40],  # Outside workspace bounds
]

for pose in unreachable_poses:
    try:
        controller.move_arm_absolute_pose(robot_id=0, position=pose)
        print(f"✅ Reached {pose}")
    except Exception as e:
        print(f"❌ Failed to reach {pose}: {e}")
```

### Joint Singularities
Certain poses may cause computational difficulties:
- **Wrist singularities**: When wrist joints align
- **Shoulder singularities**: When shoulder and elbow align
- **Workspace boundaries**: Poses at extreme reach

### Error Handling
```python
try:
    success = controller.move_arm_absolute_pose(
        robot_id=0,
        position=[0.35, 0.25, 0.05],  # Challenging pose
        max_trials=3                   # Try multiple times
    )
    if success:
        print("✅ IK succeeded")
    else:
        print("❌ IK failed after 3 attempts")
except Exception as e:
    print(f"❌ IK error: {e}")
```

## Practical Tips

### 1. Start Simple
```python
# Begin with neutral orientations
controller.move_arm_absolute_pose(
    robot_id=0,
    position=[0.25, 0.15, 0.20],
    orientation=[0, 0, 0]  # Neutral orientation first
)
```

### 2. Use Incremental Movements
```python
# Move gradually for complex poses
current_pos = [0.20, 0.10, 0.15]
target_pos = [0.35, 0.25, 0.25]

# Create intermediate steps
for i in range(1, 4):
    alpha = i / 3.0
    intermediate_pos = [
        current_pos[j] * (1 - alpha) + target_pos[j] * alpha
        for j in range(3)
    ]
    controller.move_arm_absolute_pose(robot_id=0, position=intermediate_pos)
```

### 3. Monitor Precision
```python
# Verify IK accuracy
target = [0.25, 0.15, 0.20]
controller.move_arm_absolute_pose(robot_id=0, position=target)

# Check actual achieved position
actual = controller.get_current_pose(robot_id=0)
error = [(target[i] - actual[i]) for i in range(3)]
print(f"Position error: {error} (should be small)")
```

### 4. Handle IK Failures Gracefully
```python
def safe_ik_move(controller, robot_id, target_position, max_attempts=3):
    """Robust IK movement with fallback strategies."""
    
    for attempt in range(max_attempts):
        try:
            success = controller.move_arm_absolute_pose(
                robot_id=robot_id,
                position=target_position,
                max_trials=1
            )
            
            if success:
                print(f"✅ IK succeeded on attempt {attempt + 1}")
                return True
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_attempts - 1:
                # Try with relaxed tolerance
                print("Retrying with relaxed precision...")
                controller.move_arm_absolute_pose(
                    robot_id=robot_id,
                    position=target_position,
                    position_tolerance=0.02,  # More lenient
                    max_trials=1
                )
    
    print("❌ All IK attempts failed")
    return False
```

## Demo Script Features

The `inverse_kinematics_demo.py` script demonstrates:

1. **IK Basics**: How IK is automatically used in pose control
2. **Forward Kinematics**: Getting current end effector pose  
3. **IK vs Joint Control**: Why IK is more intuitive
4. **Precision Testing**: IK accuracy and error handling
5. **Multiple Solutions**: Different orientations for same position
6. **Practical Tips**: Best practices for reliable IK usage

## Key Takeaways

- **IK is automatic**: Called internally by `move_arm_absolute_pose()`
- **Think in poses**: Specify where you want the gripper, not joint angles
- **Built-in safety**: Automatic workspace and joint limit checking
- **Precision control**: Adjustable tolerance for different applications
- **Error handling**: Graceful failure for impossible poses
- **Forward kinematics**: Verify and monitor current poses

The inverse kinematics system makes robotic arm control intuitive and precise, handling the complex mathematics automatically while providing fine-grained control over movement precision and error handling.
