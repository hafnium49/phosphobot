# SO-101 Workspace Analysis and Forbidden Pose Detection

This guide explains how to understand, validate, and work within the workspace limits of the SO-101 robotic arm, including how to detect and avoid forbidden poses.

## Table of Contents
- [Quick Reference](#quick-reference)
- [Understanding the SO-101 Workspace](#understanding-the-so-101-workspace)
- [Workspace Validation Tools](#workspace-validation-tools)
- [Command Line Interface](#command-line-interface)
- [Safe Workspace Boundaries](#safe-workspace-boundaries)
- [Common Forbidden Poses](#common-forbidden-poses)
- [Pose Validation Workflow](#pose-validation-workflow)
- [Workspace Sampling and Visualization](#workspace-sampling-and-visualization)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Integration Examples](#integration-examples)

## Quick Reference

For immediate workspace validation needs, here are the most common operations:

### Quick Answer: How to Know if a Pose is Forbidden

#### Method 1: Fast Geometric Check (Recommended)
```python
from workspace_check import quick_pose_check

# Check any end effector pose
position = [0.25, 0.15, 0.20]  # x, y, z in meters
orientation = [0, 45, -30]     # roll, pitch, yaw in degrees (optional)

is_safe, reason = quick_pose_check(position, orientation)

if is_safe:
    print("✅ Pose is reachable")
else:
    print(f"❌ Forbidden pose: {reason}")
```

#### Method 2: Precise IK Validation
```python
from workspace_validator import SO101WorkspaceValidator

validator = SO101WorkspaceValidator(arm_side="left")
is_reachable, reason, data = validator.check_pose_reachability([0.30, 0.20, 0.15])

print(f"Reachable: {is_reachable}")
print(f"Reason: {reason}")
if is_reachable:
    print(f"Position error: {data['position_error']*1000:.1f}mm")

validator.controller.disconnect()
```

### SO-101 Workspace Limits (Quick Reference)

#### Safe Operating Zone
```
X (Forward):  0.08m to 0.35m    (8cm to 35cm from base)
Y (Lateral):  ±0.25m            (±25cm from centerline)
Z (Height):   0.03m to 0.32m    (3cm to 32cm above base)
```

#### Orientation Limits
```
Roll:   ±90°     (gripper roll)
Pitch:  ±90°     (gripper tilt up/down)  
Yaw:    ±180°    (gripper rotation left/right)
```

#### Maximum Reach
- **Radial distance**: ~45cm from base center
- **Minimum distance**: 5cm (collision avoidance)

### Common Forbidden Pose Types (Quick Examples)

#### 1. Outside Workspace Bounds
```python
# Too far forward
[0.45, 0.20, 0.15]  # ❌ X > 0.35m

# Too far lateral  
[0.25, 0.35, 0.20]  # ❌ Y > ±0.25m

# Too high/low
[0.25, 0.15, 0.40]  # ❌ Z > 0.32m
[0.25, 0.15, 0.01]  # ❌ Z < 0.03m
```

#### 2. Beyond Reach Limits
```python
# Too far from base
[0.40, 0.30, 0.25]  # ❌ Distance > 45cm

# Too close to base
[0.05, 0.00, 0.10]  # ❌ Distance < 5cm
```

#### 3. Excessive Orientations
```python
# Invalid orientations
[0.25, 0.15, 0.20], [120, 0, 0]    # ❌ Roll > 90°
[0.25, 0.15, 0.20], [0, 100, 0]    # ❌ Pitch > 90°
[0.25, 0.15, 0.20], [0, 0, 200]    # ❌ Yaw > 180°
```

### Quick Validation Integration

#### In Control Scripts
```python
from dual_so101_controller import DualSO101Controller

# Enable built-in validation
controller = DualSO101Controller(enable_workspace_validation=True)

# This will automatically check poses and offer alternatives
controller.move_arm_absolute_pose(
    robot_id=0,
    position=[0.25, 0.15, 0.20],
    validate_workspace=True  # Will prompt for safe alternatives
)
```

#### Batch Validation
```python
from workspace_check import validate_pose_sequence

trajectory = [
    [0.20, 0.10, 0.15],  # Start
    [0.25, 0.15, 0.20],  # Middle
    [0.30, 0.10, 0.25],  # End
]

is_valid, issues = validate_pose_sequence(trajectory)
if not is_valid:
    for issue in issues:
        print(f"⚠️  {issue}")
```

#### Safe Pose Correction
```python
from workspace_check import find_nearest_safe_pose

# If pose is forbidden, get safe alternative
target = [0.45, 0.30, 0.35]  # Forbidden pose
safe_pose, explanation = find_nearest_safe_pose(target)

print(f"Original: {target}")
print(f"Safe alternative: {safe_pose}")
print(f"Explanation: {explanation}")
```

### Quick Command Line Tools

#### Basic Pose Check
```bash
# Check specific pose
python workspace_validator.py --check-pose 0.25 0.15 0.20

# Check pose with orientation
python workspace_validator.py --check-pose-orient 0.30 0.10 0.15 0 45 -30

# Get workspace summary
python workspace_validator.py --summary
```

#### Workspace Analysis
```bash
# Sample workspace (detailed but slow)
python workspace_validator.py --sample-workspace --resolution 15

# Visualize workspace
python workspace_validator.py --visualize

# Run all demos
python workspace_demo.py
```

### Quick Best Practices

#### 1. Always Validate First
```python
# Don't do this
controller.move_arm_absolute_pose(robot_id=0, position=unknown_pose)

# Do this  
is_safe, reason = quick_pose_check(unknown_pose)
if is_safe:
    controller.move_arm_absolute_pose(robot_id=0, position=unknown_pose)
else:
    print(f"Unsafe pose: {reason}")
```

#### 2. Use Conservative Bounds
```python
# For critical applications, reduce workspace bounds
SAFE_BOUNDS = {
    'x': (0.10, 0.30),  # More conservative
    'y': (-0.20, 0.20), # Smaller lateral range
    'z': (0.05, 0.25),  # Lower height range
}
```

#### 3. Plan Smooth Trajectories
```python
# Check entire trajectory, not just endpoints
waypoints = generate_trajectory(start, end, num_points=10)
is_valid, issues = validate_pose_sequence(waypoints)
```

### Quick Troubleshooting

#### "Pose appears reachable" but robot can't reach it
- Geometric check passed but IK failed
- Try reducing position tolerance
- Check for joint singularities
- Use precise IK validation

#### "Position error too large"
- Target near workspace boundary
- Joint limits preventing exact positioning
- Try alternative orientation
- Move closer to workspace center

#### Unexpected forbidden poses
- Check coordinate units (meters vs cm)
- Verify workspace calibration
- Consider arm mounting position
- Account for gripper/tool dimensions

**💡 This validation system helps ensure safe and reliable operation by catching forbidden poses before they're sent to the robot.**

---

## Understanding the SO-101 Workspace

### Physical Constraints

The SO-101 is a 5-DOF robotic arm with the following specifications:
- **Total reach**: ~45cm from base center (maximum radial distance)
- **Minimum reach**: ~5cm (to avoid base collision)
- **Safe height range**: 3cm to 32cm above base
- **Safe lateral range**: ±25cm from arm centerline
- **Position tolerance**: ±5mm for end effector positioning
- **Orientation tolerance**: ±5.7° for end effector orientation

### Joint Configuration and Limits
```
Joint 1: shoulder_pan   (-150° to +150°)  - Base rotation
Joint 2: shoulder_lift  (-120° to +120°)  - Shoulder pitch  
Joint 3: elbow_flex     (-135° to +135°)  - Elbow bend
Joint 4: wrist_flex     (-120° to +120°)  - Wrist pitch
Joint 5: wrist_roll     (-180° to +180°)  - Gripper rotation
Joint 6: gripper        (0 to 1)          - Gripper open/close (0=closed, 1=open)
```

### Coordinate System
- **X-axis**: Forward direction from base (positive = away from base)
- **Y-axis**: Lateral direction (positive = left side when facing forward)
- **Z-axis**: Vertical direction (positive = upward)
- **Origin**: Base center at ground level
- **Units**: Positions in meters, orientations in degrees

## Workspace Validation Tools

This package provides three levels of workspace validation:

### 1. Quick Pose Check (Fast - Recommended for Real-Time)

For rapid validation without running inverse kinematics:

```python
from workspace_check import quick_pose_check

# Check a single pose
position = [0.25, 0.15, 0.20]  # x, y, z in meters
is_safe, reason = quick_pose_check(position)

if is_safe:
    print(f"✅ Pose {position} is likely reachable")
else:
    print(f"❌ Pose {position} is unsafe: {reason}")

# Check pose with orientation
orientation = [0, 45, -30]  # roll, pitch, yaw in degrees
is_safe, reason = quick_pose_check(position, orientation)
```

**Features:**
- Sub-millisecond validation
- Geometric boundary checks
- Radial distance validation
- Orientation limit checking
- No robot connection required

### 2. Full IK Validation (Precise - For Critical Applications)

For precise validation using inverse kinematics simulation:

```python
from workspace_validator import SO101WorkspaceValidator

validator = SO101WorkspaceValidator(arm_side="left")

# Precise reachability check
position = [0.30, 0.20, 0.15]
is_reachable, reason, data = validator.check_pose_reachability(position)

if is_reachable:
    print(f"✅ Pose precisely reachable")
    print(f"   Position error: {data['position_error']*1000:.1f}mm")
    print(f"   IK solution: {data['ik_solution']}")
else:
    print(f"❌ Pose unreachable: {reason}")

# Cleanup
validator.controller.disconnect()
```

**Features:**
- PyBullet-based inverse kinematics
- Forward kinematics verification
- Joint limit checking
- Precision measurement (sub-millimeter)
- Detailed error reporting

### 3. Integrated Controller Validation

Built into the DualSO101Controller for seamless operation:

```python
from dual_so101_controller import DualSO101Controller

# Initialize with validation enabled (default)
controller = DualSO101Controller(enable_workspace_validation=True)

# Automatic validation with user prompts for corrections
controller.move_arm_absolute_pose(
    robot_id=0,
    position=[0.25, 0.15, 0.20],
    validate_workspace=True  # Will prompt for safe alternatives if needed
)

# Manual validation without moving
is_valid, reason = controller.validate_pose([0.30, 0.20, 0.15])
print(f"Valid: {is_valid}, Reason: {reason}")

controller.disconnect()
```

**Features:**
- Automatic pose correction suggestions
- Interactive user prompts
- Seamless integration with movement commands
- Option to disable for automated systems

### 2. Full IK Validation (Precise)

For precise validation using inverse kinematics:

```python
from workspace_validator import SO101WorkspaceValidator

validator = SO101WorkspaceValidator(arm_side="left")

# Precise reachability check
position = [0.30, 0.20, 0.15]
is_reachable, reason, data = validator.check_pose_reachability(position)

if is_reachable:
    print(f"✅ Pose precisely reachable")
    print(f"   Position error: {data['position_error']*1000:.1f}mm")
else:
    print(f"❌ Pose unreachable: {reason}")

# Cleanup
validator.controller.disconnect()
```

## Command Line Interface

The package includes comprehensive command-line tools for workspace analysis:

### Basic Pose Validation
```bash
# Check if a specific pose is reachable
python workspace_validator.py --check-pose 0.25 0.15 0.20

# Check pose with orientation
python workspace_validator.py --check-pose-orient 0.30 0.10 0.15 0 45 -30

# Get workspace boundaries and summary
python workspace_validator.py --summary
```

### Workspace Analysis and Visualization
```bash
# Sample the entire workspace (detailed analysis)
python workspace_validator.py --sample-workspace --resolution 15

# Visualize workspace in 3D
python workspace_validator.py --visualize

# Load and visualize existing sample data
python workspace_validator.py --visualize --load-sample workspace_sample_left_15.json
```

### Interactive Demonstrations
```bash
# Run comprehensive workspace validation demos
python workspace_demo.py

# Quick workspace summary and examples
python -c "from workspace_check import print_workspace_summary; print_workspace_summary()"
```

### Example Command Outputs
```bash
$ python workspace_validator.py --check-pose 0.25 0.15 0.20
🎯 Checking pose reachability: [0.25, 0.15, 0.20]
✅ Pose is reachable
   Position error: 2.3mm

$ python workspace_validator.py --summary
📋 SO-101 Left Arm Workspace Summary:
   Max forward reach: 0.35m
   Max lateral reach: ±0.25m
   Height range: 0.03m to 0.32m
   Position tolerance: 5.0mm
   Orientation tolerance: 5.7°
```

## Command Line Interface

### Overview

The command line interface (CLI) for workspace validation provides tools for:
- Sampling the workspace at various resolutions
- Visualizing the workspace and forbidden zones
- Checking specific poses or pose sequences
- Getting a summary of the workspace analysis

### Commands

```bash
# Sample workspace with default settings
python workspace_validator.py --sample-workspace

# Sample workspace at a specific resolution
python workspace_validator.py --sample-workspace --resolution 10

# Visualize the sampled workspace
python workspace_validator.py --visualize

# Check a specific pose
python workspace_validator.py --check-pose 0.25 0.15 0.20

# Check a pose with orientation
python workspace_validator.py --check-pose-orient 0.30 0.10 0.15 0 45 -30

# Get a summary of the workspace analysis
python workspace_validator.py --summary
```

## Safe Workspace Boundaries

### Conservative Bounds (Recommended for Production)
```python
SAFE_WORKSPACE = {
    'x': (0.08, 0.35),    # Forward: 8cm to 35cm from base
    'y': (-0.25, 0.25),   # Lateral: ±25cm from centerline
    'z': (0.03, 0.32),    # Height: 3cm to 32cm above base
}

# Maximum radial reach: ~45cm from base center
# Minimum radial reach: ~5cm (collision avoidance)
```

### Orientation Limits (Practical Working Ranges)
```python
ORIENTATION_LIMITS = {
    'roll': (-90, 90),    # ±90° gripper roll
    'pitch': (-90, 90),   # ±90° gripper pitch  
    'yaw': (-180, 180),   # ±180° gripper yaw rotation
}
```

### Working Zones by Confidence Level

**Inner Zone (High Confidence - 95%+ Success Rate)**
```python
inner_zone = {
    'x': (0.15, 0.30),    # 15cm to 30cm forward
    'y': (-0.20, 0.20),   # ±20cm lateral
    'z': (0.05, 0.25),    # 5cm to 25cm height
}
```
- **Use for**: Precision tasks, delicate operations, production work
- **Characteristics**: Reliable positioning, stable joint configurations
- **Typical precision**: ±2mm position, ±2° orientation

**Outer Zone (Moderate Confidence - 80%+ Success Rate)**  
```python
outer_zone = {
    'x': (0.08, 0.35),    # 8cm to 35cm forward
    'y': (-0.25, 0.25),   # ±25cm lateral
    'z': (0.03, 0.32),    # 3cm to 32cm height
}
```
- **Use for**: General manipulation, larger movements, setup tasks
- **Characteristics**: Generally reliable, some precision limitations near boundaries
- **Typical precision**: ±5mm position, ±5° orientation

**Extended Zone (Low Confidence - Testing Only)**
```python
extended_zone = {
    'x': (0.05, 0.40),    # Beyond recommended bounds
    'y': (-0.30, 0.30),   # Extended lateral reach
    'z': (0.01, 0.35),    # Extended height range
}
```
- **Use for**: Testing, exploration, emergency recovery (with extreme caution)
- **Characteristics**: Unpredictable success, potential joint limit issues
- **Typical precision**: ±10mm+ position, ±10°+ orientation

### Workspace Volume Analysis
```python
from workspace_check import get_workspace_volume, get_workspace_center

# Get workspace characteristics
volume = get_workspace_volume()  # ~0.039 m³
center = get_workspace_center()  # [0.21, 0.00, 0.17]

print(f"Workspace volume: {volume:.4f} m³")
print(f"Workspace center: {center}")
```

## Common Forbidden Poses

Understanding why poses become forbidden helps in planning safe trajectories and avoiding common pitfalls.

### 1. Geometric Boundary Violations

**Outside Safe Workspace Bounds**
```python
# X-axis violations (forward/backward)
forbidden_x = [
    [0.05, 0.00, 0.15],   # Too close to base (X < 0.08m)
    [0.40, 0.10, 0.20],   # Too far forward (X > 0.35m)
]

# Y-axis violations (lateral)
forbidden_y = [
    [0.25, 0.30, 0.15],   # Too far left (Y > 0.25m)
    [0.25, -0.30, 0.15],  # Too far right (Y < -0.25m)
]

# Z-axis violations (height)
forbidden_z = [
    [0.20, 0.10, 0.01],   # Too low - ground collision risk (Z < 0.03m)
    [0.20, 0.10, 0.35],   # Too high (Z > 0.32m)
]
```

### 2. Radial Distance Limits

**Beyond Maximum Reach (>45cm from base)**
```python
# Calculate radial distance: sqrt(x² + y² + z²)
forbidden_reach = [
    [0.40, 0.30, 0.25],   # Distance: 0.58m > 0.45m limit
    [0.35, 0.25, 0.30],   # Distance: 0.52m > 0.45m limit
    [0.30, 0.35, 0.20],   # Distance: 0.54m > 0.45m limit
]

# Too close to base (<5cm minimum)
forbidden_close = [
    [0.03, 0.02, 0.08],   # Distance: 0.09m < 0.05m limit
    [0.04, 0.00, 0.00],   # Distance: 0.04m < 0.05m limit
]
```

### 3. Orientation Limit Violations

**Excessive Joint Rotations**
```python
# Orientation format: [roll, pitch, yaw] in degrees
forbidden_orientations = [
    ([0.25, 0.15, 0.20], [120, 0, 0]),    # Roll > 90°
    ([0.25, 0.15, 0.20], [0, 100, 0]),    # Pitch > 90°
    ([0.25, 0.15, 0.20], [0, 0, 200]),    # Yaw > 180°
    ([0.25, 0.15, 0.20], [-100, 0, 0]),   # Roll < -90°
]
```

### 4. Complex Geometric Constraints

**Extreme Position Combinations**
```python
# These combinations are geometrically impossible for SO-101
forbidden_combinations = [
    [0.35, 0.25, 0.05],   # Max forward + max lateral + very low
    [0.08, 0.25, 0.30],   # Close + max lateral + high
    [0.35, 0.00, 0.32],   # Max forward + max height
]
```

### 5. Joint Singularity Regions

**Wrist Singularities**
- Occur when wrist joints align, causing loss of controllability
- Symptoms: Erratic movement, large joint angle changes for small end effector movements
- Common locations: Fully extended positions, certain overhead poses

**Shoulder Singularities**
- When shoulder and elbow joints align
- Common at extreme forward/backward reaches
- May cause sudden joint flips

```python
# Poses prone to singularities (use with caution)
singularity_prone = [
    [0.35, 0.00, 0.15],   # Fully extended forward
    [0.10, 0.00, 0.30],   # Overhead near base
    [0.30, 0.00, 0.02],   # Extended + very low
]
```

### 6. Collision Scenarios

**Base Collision Risks**
```python
# Poses that may cause arm-to-base collision
base_collision_risk = [
    [0.08, 0.00, 0.04],   # Low + close to base
    [0.05, 0.10, 0.08],   # Very close + lateral offset
]
```

**Ground Collision Risks**
```python
# Poses below safe ground clearance
ground_collision_risk = [
    [0.25, 0.15, 0.02],   # Below 3cm safety margin
    [0.30, 0.20, 0.01],   # At ground level
    [0.20, 0.10, -0.01],  # Below ground plane
]
```

### 7. Detection and Prevention

**Automatic Detection**
```python
from workspace_check import quick_pose_check

def analyze_forbidden_pose(position, orientation=None):
    """Analyze why a pose is forbidden."""
    is_safe, reason = quick_pose_check(position, orientation)
    
    if not is_safe:
        print(f"❌ Forbidden pose: {position}")
        print(f"   Reason: {reason}")
        
        # Get safe alternative
        from workspace_check import find_nearest_safe_pose
        safe_pose, explanation = find_nearest_safe_pose(position)
        print(f"   Safe alternative: {safe_pose}")
        print(f"   Correction: {explanation}")
        
        return False, reason, safe_pose
    
    return True, "Pose is safe", position

# Example usage
forbidden_pose = [0.45, 0.30, 0.35]
is_safe, reason, alternative = analyze_forbidden_pose(forbidden_pose)
```

**Batch Analysis**
```python
from workspace_check import validate_pose_sequence

# Check entire trajectory for forbidden poses
trajectory = [
    [0.20, 0.10, 0.15],   # Start
    [0.40, 0.25, 0.30],   # Forbidden middle point
    [0.25, 0.15, 0.20],   # End
]

is_valid, issues = validate_pose_sequence(trajectory)
if not is_valid:
    print("Trajectory contains forbidden poses:")
    for issue in issues:
        print(f"  • {issue}")
```

## Pose Validation Workflow

### 1. Development Phase Validation

**Interactive Development**
```python
from workspace_check import quick_pose_check, find_nearest_safe_pose

def interactive_pose_planning():
    """Interactive pose planning with validation."""
    while True:
        try:
            # Get user input
            x = float(input("Enter X position (m): "))
            y = float(input("Enter Y position (m): "))
            z = float(input("Enter Z position (m): "))
            
            position = [x, y, z]
            
            # Validate pose
            is_safe, reason = quick_pose_check(position)
            
            if is_safe:
                print(f"✅ Pose {position} is safe!")
                break
            else:
                print(f"❌ Unsafe pose: {reason}")
                
                # Offer safe alternative
                safe_pose, explanation = find_nearest_safe_pose(position)
                print(f"💡 Suggested safe pose: {safe_pose}")
                print(f"   {explanation}")
                
                if input("Use safe pose? (y/n): ").lower() == 'y':
                    position = safe_pose
                    break
                    
        except ValueError:
            print("Invalid input. Please enter numeric values.")
        except KeyboardInterrupt:
            print("\nPlanning cancelled.")
            return None
    
    return position
```

### 2. Pre-Movement Validation

**Safe Movement Function**
```python
from workspace_check import quick_pose_check, find_nearest_safe_pose
from dual_so101_controller import DualSO101Controller

def safe_move_to_pose(controller, robot_id, target_pose, orientation=None, auto_correct=False):
    """Move to pose with comprehensive validation."""
    
    # Step 1: Quick geometric check
    is_safe, reason = quick_pose_check(target_pose, orientation)
    
    if not is_safe:
        print(f"❌ Unsafe pose: {reason}")
        
        if auto_correct:
            # Automatic correction for automated systems
            safe_pose, explanation = find_nearest_safe_pose(target_pose)
            print(f"🔧 Auto-corrected to: {safe_pose}")
            print(f"   {explanation}")
            target_pose = safe_pose
        else:
            # Interactive correction for manual operation
            safe_pose, explanation = find_nearest_safe_pose(target_pose)
            print(f"💡 Safe alternative: {safe_pose}")
            print(f"   {explanation}")
            
            response = input("Use safe pose? (y/n): ").lower()
            if response == 'y':
                target_pose = safe_pose
            else:
                print("Movement cancelled.")
                return False
    
    # Step 2: Execute movement with built-in validation
    try:
        success = controller.move_arm_absolute_pose(
            robot_id=robot_id,
            position=target_pose,
            orientation=orientation,
            validate_workspace=True
        )
        
        if success:
            print(f"✅ Successfully moved to {target_pose}")
            return True
        else:
            print(f"❌ Movement failed")
            return False
            
    except Exception as e:
        print(f"❌ Movement error: {e}")
        return False
```

### 3. Trajectory Validation

**Multi-Waypoint Planning**
```python
from workspace_check import validate_pose_sequence, quick_pose_check

def plan_safe_trajectory(waypoints, max_jump_distance=0.15):
    """Plan and validate a complete trajectory."""
    
    print(f"🛤️  Planning trajectory with {len(waypoints)} waypoints...")
    
    # Validate entire sequence
    all_valid, issues = validate_pose_sequence(waypoints)
    
    if not all_valid:
        print("❌ Trajectory validation failed:")
        for issue in issues:
            print(f"   • {issue}")
        
        # Attempt to fix issues
        print("\n🔧 Attempting trajectory correction...")
        corrected_waypoints = []
        
        for i, waypoint in enumerate(waypoints):
            is_safe, reason = quick_pose_check(waypoint)
            
            if is_safe:
                corrected_waypoints.append(waypoint)
            else:
                print(f"   Correcting waypoint {i+1}: {reason}")
                safe_pose, _ = find_nearest_safe_pose(waypoint)
                corrected_waypoints.append(safe_pose)
        
        # Validate corrected trajectory
        all_valid, issues = validate_pose_sequence(corrected_waypoints)
        
        if all_valid:
            print("✅ Trajectory corrected successfully!")
            return corrected_waypoints
        else:
            print("❌ Could not create safe trajectory")
            return None
    
    else:
        print("✅ Trajectory is valid!")
        return waypoints

def execute_trajectory(controller, robot_id, waypoints):
    """Execute validated trajectory with safety checks."""
    
    # Plan trajectory
    safe_waypoints = plan_safe_trajectory(waypoints)
    if safe_waypoints is None:
        return False
    
    # Execute waypoints
    print(f"\n🚀 Executing trajectory...")
    for i, waypoint in enumerate(safe_waypoints):
        print(f"   Moving to waypoint {i+1}/{len(safe_waypoints)}: {waypoint}")
        
        success = safe_move_to_pose(
            controller, robot_id, waypoint, auto_correct=True
        )
        
        if not success:
            print(f"❌ Failed at waypoint {i+1}")
            return False
        
        # Brief pause between waypoints
        time.sleep(0.5)
    
    print("✅ Trajectory completed successfully!")
    return True
```

### 4. Production System Integration

**Robust Production Wrapper**
```python
def production_pose_control(controller, robot_id, target_pose, max_attempts=3):
    """Production-ready pose control with comprehensive error handling."""
    
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1}/{max_attempts}")
            
            # Step 1: Validate pose
            is_valid = controller.validate_pose(target_pose)
            if not is_valid[0]:
                raise ValueError(f"Invalid pose: {is_valid[1]}")
            
            # Step 2: Attempt movement
            success = controller.move_arm_absolute_pose(
                robot_id=robot_id,
                position=target_pose,
                validate_workspace=False,  # Already validated above
                max_trials=1  # Single attempt per validation cycle
            )
            
            if success:
                # Step 3: Verify final position
                current_pose = controller.get_current_pose(robot_id)
                position_error = np.linalg.norm(
                    np.array(target_pose) - np.array(current_pose['position'])
                )
                
                if position_error < 0.01:  # 1cm tolerance
                    print(f"✅ Pose achieved with {position_error*1000:.1f}mm error")
                    return True
                else:
                    print(f"⚠️  Large position error: {position_error*1000:.1f}mm")
                    if attempt < max_attempts - 1:
                        print("Retrying with higher precision...")
                        continue
                    else:
                        return False
                        
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                print("Retrying...")
                time.sleep(1.0)
            else:
                print("All attempts failed")
                return False
    
    return False
```

## Workspace Sampling and Visualization

### Comprehensive Workspace Analysis

**Full Workspace Sampling**
```bash
# High-resolution sampling (takes ~5-10 minutes)
python workspace_validator.py --sample-workspace --resolution 20

# Medium resolution for quick analysis (~30 seconds)
python workspace_validator.py --sample-workspace --resolution 15

# Low resolution for rapid testing (~5 seconds)  
python workspace_validator.py --sample-workspace --resolution 10
```

**Sample Output**
```
🔍 Sampling left arm workspace...
   Grid resolution: 15³ = 3,375 points
   Progress: 3,375/3,375 (100.0%) - ETA: 0s

📊 Workspace Sampling Results:
   Reachable points: 2,127/3,375 (63.0%)
   Sampling time: 45.2s
   Results saved to: workspace_sample_left_15.json
```

**3D Visualization**
```bash
# Visualize existing sample data
python workspace_validator.py --visualize

# Visualize specific sample file
python workspace_validator.py --visualize --load-sample workspace_sample_left_20.json
```

### Custom Workspace Analysis

**Programmatic Sampling**
```python
from workspace_validator import SO101WorkspaceValidator

# Initialize validator
validator = SO101WorkspaceValidator(arm_side="left")

# Custom sampling with specific parameters
sample_data = validator.sample_workspace(
    grid_resolution=12,
    save_results=True
)

# Analyze results
print(f"Reachable percentage: {sample_data['reachable_percentage']:.1f}%")
print(f"Total points tested: {sample_data['total_points']:,}")
print(f"Reachable points: {sample_data['reachable_count']:,}")

# Visualize results
validator.visualize_workspace(sample_data=sample_data)

validator.controller.disconnect()
```

**Workspace Boundary Analysis**
```python
# Test specific boundary regions
boundary_tests = [
    ("X minimum", [0.08, 0.00, 0.15]),
    ("X maximum", [0.35, 0.00, 0.15]),
    ("Y minimum", [0.25, -0.25, 0.15]),
    ("Y maximum", [0.25, 0.25, 0.15]),
    ("Z minimum", [0.25, 0.00, 0.03]),
    ("Z maximum", [0.25, 0.00, 0.32]),
]

for name, position in boundary_tests:
    is_reachable, reason, data = validator.check_pose_reachability(position)
    print(f"{name}: {'✅' if is_reachable else '❌'} {reason}")
```

### Workspace Characterization

**Statistical Analysis**
```python
def analyze_workspace_statistics(sample_data):
    """Analyze workspace statistics from sampling data."""
    
    reachable_points = np.array([p['position'] for p in sample_data['reachable_points']])
    
    if len(reachable_points) == 0:
        print("No reachable points found!")
        return
    
    # Calculate workspace characteristics
    x_coords = reachable_points[:, 0]
    y_coords = reachable_points[:, 1]
    z_coords = reachable_points[:, 2]
    
    stats = {
        'x_range': (x_coords.min(), x_coords.max()),
        'y_range': (y_coords.min(), y_coords.max()),
        'z_range': (z_coords.min(), z_coords.max()),
        'centroid': [x_coords.mean(), y_coords.mean(), z_coords.mean()],
        'volume_estimate': len(reachable_points) / sample_data['total_points'] * 
                          get_workspace_volume(),
        'reachable_percentage': sample_data['reachable_percentage']
    }
    
    print("📊 Workspace Statistics:")
    print(f"   X range: {stats['x_range'][0]:.3f}m to {stats['x_range'][1]:.3f}m")
    print(f"   Y range: {stats['y_range'][0]:.3f}m to {stats['y_range'][1]:.3f}m") 
    print(f"   Z range: {stats['z_range'][0]:.3f}m to {stats['z_range'][1]:.3f}m")
    print(f"   Centroid: [{stats['centroid'][0]:.3f}, {stats['centroid'][1]:.3f}, {stats['centroid'][2]:.3f}]")
    print(f"   Estimated volume: {stats['volume_estimate']:.4f} m³")
    print(f"   Reachability: {stats['reachable_percentage']:.1f}%")
    
    return stats
```

### Interactive Visualization Tools

**Custom 3D Plotting**
```python
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

def create_custom_workspace_plot(sample_data, show_unreachable=False):
    """Create customized 3D workspace visualization."""
    
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Extract point data
    reachable = np.array([p['position'] for p in sample_data['reachable_points']])
    unreachable = np.array([p['position'] for p in sample_data['unreachable_points']])
    
    # Plot reachable points
    if len(reachable) > 0:
        ax.scatter(reachable[:, 0], reachable[:, 1], reachable[:, 2],
                  c='green', alpha=0.6, s=15, label=f'Reachable ({len(reachable)})')
    
    # Plot unreachable points (optional)
    if show_unreachable and len(unreachable) > 0:
        ax.scatter(unreachable[:, 0], unreachable[:, 1], unreachable[:, 2],
                  c='red', alpha=0.2, s=5, label=f'Unreachable ({len(unreachable)})')
    
    # Add workspace boundary box
    bounds = get_safe_workspace_bounds()
    
    # Create boundary box
    x_bounds = [bounds['x'][0], bounds['x'][1]]
    y_bounds = [bounds['y'][0], bounds['y'][1]]
    z_bounds = [bounds['z'][0], bounds['z'][1]]
    
    # Draw boundary edges
    for x in x_bounds:
        for y in y_bounds:
            ax.plot([x, x], [y, y], z_bounds, 'b--', alpha=0.3, linewidth=1)
    
    for x in x_bounds:
        for z in z_bounds:
            ax.plot([x, x], y_bounds, [z, z], 'b--', alpha=0.3, linewidth=1)
    
    for y in y_bounds:
        for z in z_bounds:
            ax.plot(x_bounds, [y, y], [z, z], 'b--', alpha=0.3, linewidth=1)
    
    # Formatting
    ax.set_xlabel('X (m) - Forward')
    ax.set_ylabel('Y (m) - Lateral')
    ax.set_zlabel('Z (m) - Height')
    ax.set_title(f'SO-101 {sample_data["arm_side"].title()} Arm Workspace\n'
                f'Resolution: {sample_data["grid_resolution"]}³, '
                f'Reachable: {sample_data["reachable_count"]:,}/{sample_data["total_points"]:,} '
                f'({sample_data.get("reachable_percentage", 0):.1f}%)')
    
    ax.legend()
    
    # Set equal aspect ratio
    max_range = max(bounds['x'][1] - bounds['x'][0],
                   bounds['y'][1] - bounds['y'][0],
                   bounds['z'][1] - bounds['z'][0]) / 2
    
    mid_x = (bounds['x'][0] + bounds['x'][1]) / 2
    mid_y = (bounds['y'][0] + bounds['y'][1]) / 2
    mid_z = (bounds['z'][0] + bounds['z'][1]) / 2
    
    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)
    
    plt.tight_layout()
    plt.show()
```

## Best Practices

### 1. Development Guidelines

**Always Validate First**
```python
# ❌ Don't do this
def unsafe_move(controller, position):
    return controller.move_arm_absolute_pose(0, position)

# ✅ Do this
def safe_move(controller, position):
    is_safe, reason = quick_pose_check(position)
    if not is_safe:
        print(f"Unsafe pose rejected: {reason}")
        return False
    return controller.move_arm_absolute_pose(0, position, validate_workspace=True)
```

**Use Incremental Testing**
```python
def incremental_workspace_exploration():
    """Safely explore workspace boundaries."""
    
    # Start from known safe center
    center = [0.20, 0.00, 0.15]
    step_size = 0.02  # 2cm steps
    
    # Test different directions
    directions = {
        'forward': [1, 0, 0],
        'backward': [-1, 0, 0],
        'left': [0, 1, 0],
        'right': [0, -1, 0],
        'up': [0, 0, 1],
        'down': [0, 0, -1],
    }
    
    for direction_name, direction_vector in directions.items():
        print(f"\nTesting {direction_name} direction:")
        position = center.copy()
        
        for step in range(1, 20):  # Up to 38cm from center
            # Take step in direction
            for i in range(3):
                position[i] += direction_vector[i] * step_size
            
            # Test position
            is_safe, reason = quick_pose_check(position)
            
            if is_safe:
                print(f"  Step {step}: {position} ✅")
            else:
                print(f"  Step {step}: {position} ❌ - {reason}")
                print(f"  Maximum {direction_name} reach: ~{(step-1)*step_size*100:.0f}cm")
                break
```

**Layer Validation Approaches**
```python
def multi_layer_validation(position, orientation=None):
    """Apply multiple validation layers for critical applications."""
    
    # Layer 1: Quick geometric check
    is_safe_geom, reason_geom = quick_pose_check(position, orientation)
    if not is_safe_geom:
        return False, f"Geometric check failed: {reason_geom}"
    
    # Layer 2: Conservative bounds check
    conservative_bounds = {
        'x': (0.10, 0.30),  # More restrictive
        'y': (-0.20, 0.20),
        'z': (0.05, 0.25),
    }
    
    x, y, z = position
    if not (conservative_bounds['x'][0] <= x <= conservative_bounds['x'][1]):
        return False, f"Outside conservative X bounds: {x:.3f}m"
    if not (conservative_bounds['y'][0] <= y <= conservative_bounds['y'][1]):
        return False, f"Outside conservative Y bounds: {y:.3f}m"
    if not (conservative_bounds['z'][0] <= z <= conservative_bounds['z'][1]):
        return False, f"Outside conservative Z bounds: {z:.3f}m"
    
    # Layer 3: Precise IK validation (if available)
    try:
        validator = SO101WorkspaceValidator()
        is_reachable, reason_ik, data = validator.check_pose_reachability(
            position, orientation, verbose=False
        )
        validator.controller.disconnect()
        
        if not is_reachable:
            return False, f"IK validation failed: {reason_ik}"
        
        # Check precision
        if data.get('position_error', 0) > 0.003:  # 3mm tolerance
            return False, f"IK precision insufficient: {data['position_error']*1000:.1f}mm error"
        
    except Exception as e:
        # Fall back to geometric validation if IK unavailable
        print(f"Warning: IK validation unavailable: {e}")
    
    return True, "All validation layers passed"
```

### 2. Production System Guidelines

**Robust Error Handling**
```python
def production_workspace_validation():
    """Production-ready validation with comprehensive error handling."""
    
    class WorkspaceValidator:
        def __init__(self, max_retries=3, timeout=30):
            self.max_retries = max_retries
            self.timeout = timeout
            self.validation_cache = {}
        
        def validate_with_cache(self, position, orientation=None):
            """Validate with caching for repeated poses."""
            cache_key = f"{position}_{orientation}"
            
            if cache_key in self.validation_cache:
                return self.validation_cache[cache_key]
            
            result = quick_pose_check(position, orientation)
            self.validation_cache[cache_key] = result
            return result
        
        def validate_with_retry(self, position, orientation=None):
            """Validate with retry logic for transient failures."""
            for attempt in range(self.max_retries):
                try:
                    return self.validate_with_cache(position, orientation)
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        print(f"Validation attempt {attempt + 1} failed: {e}")
                        time.sleep(0.1)
                    else:
                        raise
        
        def clear_cache(self):
            """Clear validation cache."""
            self.validation_cache.clear()
```

**Automated Pose Correction**
```python
def automated_pose_correction(target_poses, tolerance=0.01):
    """Automatically correct invalid poses in a batch."""
    
    corrected_poses = []
    corrections_made = []
    
    for i, pose in enumerate(target_poses):
        is_safe, reason = quick_pose_check(pose)
        
        if is_safe:
            corrected_poses.append(pose)
        else:
            # Attempt correction
            safe_pose, explanation = find_nearest_safe_pose(pose)
            
            # Check if correction is within tolerance
            correction_distance = np.linalg.norm(
                np.array(safe_pose) - np.array(pose)
            )
            
            if correction_distance <= tolerance:
                corrected_poses.append(safe_pose)
                corrections_made.append({
                    'index': i,
                    'original': pose,
                    'corrected': safe_pose,
                    'distance': correction_distance,
                    'reason': reason
                })
            else:
                raise ValueError(
                    f"Pose {i} requires correction beyond tolerance: "
                    f"{correction_distance:.3f}m > {tolerance:.3f}m"
                )
    
    return corrected_poses, corrections_made
```

### 3. Performance Optimization

**Batch Validation**
```python
def batch_validate_poses(poses, use_parallel=True):
    """Efficiently validate multiple poses."""
    
    if use_parallel:
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(
                lambda pose: quick_pose_check(pose), poses
            ))
    else:
        results = [quick_pose_check(pose) for pose in poses]
    
    # Analyze results
    valid_count = sum(1 for is_safe, _ in results if is_safe)
    invalid_poses = [
        (i, pose, reason) for i, (pose, (is_safe, reason)) 
        in enumerate(zip(poses, results)) if not is_safe
    ]
    
    return {
        'total': len(poses),
        'valid': valid_count,
        'invalid': len(invalid_poses),
        'success_rate': valid_count / len(poses) * 100,
        'invalid_details': invalid_poses
    }
```

**Workspace Precomputation**
```python
def precompute_workspace_grid(resolution=20, save_path="workspace_grid.json"):
    """Precompute workspace grid for fast lookup."""
    
    bounds = get_safe_workspace_bounds()
    
    # Create grid
    x_points = np.linspace(bounds['x'][0], bounds['x'][1], resolution)
    y_points = np.linspace(bounds['y'][0], bounds['y'][1], resolution)
    z_points = np.linspace(bounds['z'][0], bounds['z'][1], resolution)
    
    grid = {}
    total_points = resolution ** 3
    
    print(f"Precomputing {total_points:,} point workspace grid...")
    
    for i, x in enumerate(x_points):
        for j, y in enumerate(y_points):
            for k, z in enumerate(z_points):
                position = [float(x), float(y), float(z)]
                is_safe, _ = quick_pose_check(position)
                
                grid[f"{x:.3f},{y:.3f},{z:.3f}"] = is_safe
        
        if i % 5 == 0:
            print(f"Progress: {i}/{len(x_points)} X-slices completed")
    
    # Save grid
    with open(save_path, 'w') as f:
        json.dump(grid, f)
    
    print(f"Workspace grid saved to {save_path}")
    return grid

def lookup_workspace_grid(position, grid_file="workspace_grid.json"):
    """Fast workspace lookup using precomputed grid."""
    
    try:
        with open(grid_file, 'r') as f:
            grid = json.load(f)
        
        # Round position to grid resolution
        x, y, z = position
        key = f"{x:.3f},{y:.3f},{z:.3f}"
        
        return grid.get(key, False)  # Default to unsafe if not in grid
        
    except FileNotFoundError:
        print(f"Grid file {grid_file} not found. Run precompute_workspace_grid() first.")
        return quick_pose_check(position)[0]
```

### 4. Safety and Reliability

**Emergency Stop Integration**
```python
def workspace_with_emergency_stop(controller):
    """Integrate workspace validation with emergency stop."""
    
    class SafeController:
        def __init__(self, base_controller):
            self.controller = base_controller
            self.emergency_stop = False
            self.position_history = []
            self.max_history = 100
        
        def emergency_stop_check(self, position):
            """Check for emergency stop conditions."""
            
            # Check if moving too far from last position
            if self.position_history:
                last_pos = self.position_history[-1]
                distance = np.linalg.norm(np.array(position) - np.array(last_pos))
                
                if distance > 0.20:  # 20cm maximum jump
                    print(f"⚠️  EMERGENCY: Large position jump detected: {distance:.3f}m")
                    self.emergency_stop = True
                    return False
            
            # Check for rapid oscillation
            if len(self.position_history) >= 3:
                recent_positions = self.position_history[-3:]
                distances = [
                    np.linalg.norm(np.array(recent_positions[i]) - np.array(recent_positions[i-1]))
                    for i in range(1, len(recent_positions))
                ]
                
                if all(d > 0.05 for d in distances):  # 5cm+ movements
                    print("⚠️  EMERGENCY: Rapid oscillation detected")
                    self.emergency_stop = True
                    return False
            
            return True
        
        def safe_move(self, robot_id, position, **kwargs):
            """Move with emergency stop checking."""
            
            if self.emergency_stop:
                print("❌ Movement blocked: Emergency stop active")
                return False
            
            # Pre-movement validation
            if not self.emergency_stop_check(position):
                return False
            
            is_safe, reason = quick_pose_check(position, orientation)
            if not is_safe:
                print(f"❌ Movement blocked: {reason}")
                return False
            
            # Execute movement
            success = self.controller.move_arm_absolute_pose(
                robot_id, position, **kwargs
            )
            
            if success:
                # Update history
                self.position_history.append(position)
                if len(self.position_history) > self.max_history:
                    self.position_history.pop(0)
            
            return success
        
        def reset_emergency_stop(self):
            """Reset emergency stop (manual intervention required)."""
            print("🔄 Emergency stop reset")
            self.emergency_stop = False
            self.position_history.clear()
    
    return SafeController(controller)
```

## Troubleshooting Forbidden Poses

### Common Issues and Solutions

**"Position out of bounds" Errors**

*Problem*: Coordinates exceed safe workspace boundaries

*Solutions*:
```python
# Check coordinate units (common mistake: mm vs m)
wrong_pose = [250, 150, 200]  # ❌ Millimeters
correct_pose = [0.25, 0.15, 0.20]  # ✅ Meters

# Verify against workspace bounds
from workspace_check import get_safe_workspace_bounds, distance_to_workspace_bounds

bounds = get_safe_workspace_bounds()
print(f"Safe bounds: {bounds}")

distances = distance_to_workspace_bounds([0.40, 0.30, 0.35])
print("   Distance to boundaries:")
for boundary, distance in distances.items():
    status = "inside" if distance > 0 else "OUTSIDE"
    print(f"     {boundary}: {distance:.3f}m {status}")

# Use automatic correction
safe_pose, explanation = find_nearest_safe_pose([0.40, 0.30, 0.35])
print(f"Safe alternative: {safe_pose}")
```

**"IK solution inaccurate" Errors**

*Problem*: Target pose is near workspace boundary or requires extreme joint angles

*Solutions*:
```python
# Reduce precision requirements
controller.move_arm_absolute_pose(
    robot_id=0,
    position=[0.35, 0.25, 0.30],
    position_tolerance=0.02,    # Increased from 0.01
    orientation_tolerance=10.0  # Increased from 5.0
)

# Try alternative orientations
base_position = [0.30, 0.20, 0.15]
orientations_to_try = [
    [0, 0, 0],      # Neutral
    [0, 45, 0],     # Pitch down
    [0, -45, 0],    # Pitch up
    [0, 0, 45],     # Yaw left
    [0, 0, -45],    # Yaw right
]

for orientation in orientations_to_try:
    is_safe, reason = quick_pose_check(base_position, orientation)
    if is_safe:
        print(f"✅ Alternative orientation found: {orientation}")
        break
else:
    print("❌ No safe orientation found")

# Move position toward workspace center
from workspace_check import get_workspace_center

center = get_workspace_center()
problematic_pose = [0.35, 0.25, 0.30]

# Interpolate toward center
alpha = 0.1  # 10% toward center
corrected_pose = [
    (1 - alpha) * problematic_pose[i] + alpha * center[i]
    for i in range(3)
]

print(f"Corrected pose: {corrected_pose}")
```

**"Large jump between poses" Warnings**

*Problem*: Trajectory contains movements > 15cm between consecutive waypoints

*Solutions*:
```python
def interpolate_trajectory(start, end, max_step=0.10):
    """Create smooth trajectory with maximum step size."""
    
    distance = np.linalg.norm(np.array(end) - np.array(start))
    num_steps = max(2, int(np.ceil(distance / max_step)))
    
    waypoints = []
    for i in range(num_steps + 1):
        alpha = i / num_steps
        waypoint = [
            (1 - alpha) * start[j] + alpha * end[j]
            for j in range(3)
        ]
        waypoints.append(waypoint)
    
    return waypoints

# Example usage
large_jump_start = [0.20, 0.10, 0.15]
large_jump_end = [0.35, 0.25, 0.25]

smooth_trajectory = interpolate_trajectory(large_jump_start, large_jump_end)
print(f"Interpolated {len(smooth_trajectory)} waypoints:")
for i, waypoint in enumerate(smooth_trajectory):
    print(f"  {i}: {waypoint}")
```

**"Joint limit violation" Errors**

*Problem*: Required joint angles exceed hardware limits

*Solutions*:
```python
# Check joint limit violations in detail
def diagnose_joint_limits(position, orientation=None):
    """Diagnose which joints are causing limit violations."""
    
    try:
        validator = SO101WorkspaceValidator()
        is_reachable, reason, data = validator.check_pose_reachability(
            position, orientation, verbose=False
        )
        
        if 'joint_limit_violation' in data:
            violation = data['joint_limit_violation']
            joint_names = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 
                          'wrist_flex', 'wrist_roll']
            
            print(f"❌ Joint {violation['joint_index']+1} ({joint_names[violation['joint_index']]}) violation:")
            print(f"   Required: {violation['value']:.3f} rad ({np.degrees(violation['value']):.1f}°)")
            print(f"   Limits: [{violation['limits'][0]:.3f}, {violation['limits'][1]:.3f}] rad")
            print(f"   Limits: [{np.degrees(violation['limits'][0]):.1f}°, {np.degrees(violation['limits'][1]):.1f}°]")
        
        validator.controller.disconnect()
        
    except Exception as e:
        print(f"Could not diagnose joint limits: {e}")

# Alternative approach: reduce workspace bounds
conservative_bounds = {
    'x': (0.10, 0.30),  # More conservative
    'y': (-0.20, 0.20), # Smaller lateral range
    'z': (0.05, 0.25),  # Lower height range
}

def check_conservative_bounds(position):
    x, y, z = position
    
    if not (conservative_bounds['x'][0] <= x <= conservative_bounds['x'][1]):
        return False, f"X outside conservative bounds: {x:.3f}m"
    if not (conservative_bounds['y'][0] <= y <= conservative_bounds['y'][1]):
        return False, f"Y outside conservative bounds: {y:.3f}m"
    if not (conservative_bounds['z'][0] <= z <= conservative_bounds['z'][1]):
        return False, f"Z outside conservative bounds: {z:.3f}m"
    
    return True, "Within conservative bounds"
```

**Connection and Initialization Errors**

*Problem*: Cannot connect to robot or validation tools

*Solutions*:
```python
# Robust initialization with fallbacks
def initialize_workspace_validation(prefer_precise=True):
    """Initialize validation with graceful fallbacks."""
    
    validation_methods = []
    
    if prefer_precise:
        try:
            from workspace_validator import SO101WorkspaceValidator
            validator = SO101WorkspaceValidator()
            validation_methods.append(('precise', validator))
            print("✅ Precise IK validation available")
        except Exception as e:
            print(f"⚠️  Precise validation unavailable: {e}")
    
    # Always have geometric fallback
    from workspace_check import quick_pose_check
    validation_methods.append(('geometric', quick_pose_check))
    print("✅ Geometric validation available")
    
    return validation_methods

def validate_with_fallback(position, orientation=None):
    """Validate pose with automatic fallback to simpler methods."""
    
    validators = initialize_workspace_validation()
    
    for method_name, validator in validators:
        try:
            if method_name == 'precise':
                is_safe, reason, data = validator.check_pose_reachability(
                    position, orientation, verbose=False
                )
                return is_safe, f"{reason} (precise)", data
            
            elif method_name == 'geometric':
                is_safe, reason = validator(position, orientation)
                return is_safe, f"{reason} (geometric)", {}
            
        except Exception as e:
            print(f"Validation method '{method_name}' failed: {e}")
            continue
    
    # All methods failed
    return False, "All validation methods failed", {}
```

### Debugging Tools and Techniques

**Detailed Pose Analysis**
```python
def debug_pose_thoroughly(position, orientation=None):
    """Comprehensive pose debugging."""
    
    print(f"🔍 Debugging pose: {position}")
    if orientation:
        print(f"   Orientation: {orientation}°")
    
    # 1. Basic geometric checks
    print("\n1. Geometric Analysis:")
    bounds = get_safe_workspace_bounds()
    x, y, z = position
    
    print(f"   X: {x:.3f}m (bounds: {bounds['x'][0]:.3f} to {bounds['x'][1]:.3f})")
    print(f"   Y: {y:.3f}m (bounds: {bounds['y'][0]:.3f} to {bounds['y'][1]:.3f})")
    print(f"   Z: {z:.3f}m (bounds: {bounds['z'][0]:.3f} to {bounds['z'][1]:.3f})")
    
    # 2. Distance analysis
    print("\n2. Distance Analysis:")
    radial_distance = np.sqrt(x**2 + y**2 + z**2)
    print(f"   Radial distance: {radial_distance:.3f}m (max: 0.45m)")
    
    distances = distance_to_workspace_bounds(position)
    print("   Distance to boundaries:")
    for boundary, distance in distances.items():
        status = "✅" if distance > 0 else "❌"
        print(f"     {boundary}: {distance:.3f}m {status}")
    
    # 3. Quick validation
    print("\n3. Quick Validation:")
    is_safe, reason = quick_pose_check(position, orientation)
    print(f"   Result: {'✅' if is_safe else '❌'} {reason}")
    
    # 4. Precise validation (if available)
    print("\n4. Precise Validation:")
    try:
        validator = SO101WorkspaceValidator()
        is_reachable, reason, data = validator.check_pose_reachability(
            position, orientation, verbose=False
        )
        
        print(f"   Result: {'✅' if is_reachable else '❌'} {reason}")
        if is_reachable:
            print(f"   Position error: {data.get('position_error', 0)*1000:.1f}mm")
            if 'orientation_error' in data:
                print(f"   Orientation error: {np.degrees(data['orientation_error']):.1f}°")
        
        validator.controller.disconnect()
        
    except Exception as e:
        print(f"   ⚠️  Precise validation unavailable: {e}")
    
    # 5. Suggest corrections
    print("\n5. Suggested Corrections:")
    if not is_safe:
        safe_pose, explanation = find_nearest_safe_pose(position)
        correction_distance = np.linalg.norm(np.array(safe_pose) - np.array(position))
        print(f"   Safe alternative: {safe_pose}")
        print(f"   Correction distance: {correction_distance*1000:.1f}mm")
        print(f"   Explanation: {explanation}")

# Usage example
debug_pose_thoroughly([0.40, 0.30, 0.35], [0, 45, -30])
```

**Performance Diagnostics**
```python
def benchmark_validation_performance():
    """Benchmark validation method performance."""
    
    import time
    
    test_poses = [
        [0.20, 0.10, 0.15],  # Safe pose
        [0.30, 0.20, 0.25],  # Boundary pose
        [0.45, 0.30, 0.35],  # Forbidden pose
    ]
    
    num_iterations = 1000
    
    # Benchmark quick validation
    start_time = time.time()
    for _ in range(num_iterations):
        for pose in test_poses:
            quick_pose_check(pose)
    quick_time = time.time() - start_time
    
    print(f"📊 Validation Performance:")
    print(f"   Quick validation: {quick_time:.3f}s for {num_iterations * len(test_poses)} poses")
    print(f"   Rate: {(num_iterations * len(test_poses)) / quick_time:.0f} poses/second")
    
    # Benchmark precise validation (if available)
    try:
        validator = SO101WorkspaceValidator()
        
        start_time = time.time()
        for pose in test_poses:  # Smaller sample for precise validation
            validator.check_pose_reachability(pose, verbose=False)
        precise_time = time.time() - start_time
        
        print(f"   Precise validation: {precise_time:.3f}s for {len(test_poses)} poses")
        print(f"   Rate: {len(test_poses) / precise_time:.1f} poses/second")
        print(f"   Speedup: {precise_time / (quick_time / num_iterations):.0f}x slower than quick")
        
        validator.controller.disconnect()
        
    except Exception as e:
        print(f"   ⚠️  Precise validation benchmark unavailable: {e}")
```
