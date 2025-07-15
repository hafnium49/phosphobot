#!/usr/bin/env python3
"""
Quick Workspace Check for SO-101 Arms

This utility provides fast workspace validation and practical guidance
for SO-101 pose control without requiring extensive sampling.

Usage:
    from workspace_check import quick_pose_check, get_safe_workspace_bounds
    
    # Quick pose validation
    is_safe, reason = quick_pose_check([0.25, 0.15, 0.20])
    
    # Get conservative workspace bounds
    bounds = get_safe_workspace_bounds()
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional


# Conservative workspace bounds for SO-101 based on arm geometry
# These are safe, tested boundaries that should work reliably
SAFE_WORKSPACE_BOUNDS = {
    'x': (0.08, 0.35),    # Forward: 8cm to 35cm from base
    'y': (-0.25, 0.25),   # Lateral: ±25cm from centerline  
    'z': (0.03, 0.32),    # Height: 3cm to 32cm above base
}

# Joint limits for SO-101 (approximate, based on servo specs)
JOINT_LIMITS = {
    'shoulder_pan': (-150, 150),      # Base rotation
    'shoulder_lift': (-120, 120),     # Shoulder pitch
    'elbow_flex': (-135, 135),        # Elbow
    'wrist_flex': (-120, 120),        # Wrist pitch
    'wrist_roll': (-180, 180),        # Wrist roll (gripper rotation)
    'gripper': (0, 1),                # Gripper open/close (0=closed, 1=open)
}

# Orientation limits (degrees) - practical working ranges
ORIENTATION_LIMITS = {
    'roll': (-90, 90),    # ±90° roll
    'pitch': (-90, 90),   # ±90° pitch  
    'yaw': (-180, 180),   # ±180° yaw
}


def quick_pose_check(
    position: List[float], 
    orientation: Optional[List[float]] = None,
    workspace_bounds: Optional[Dict] = None
) -> Tuple[bool, str]:
    """
    Quick check if a pose is likely reachable without running IK.
    
    This performs fast geometric checks to filter out obviously
    unreachable poses before attempting expensive IK computation.
    
    Args:
        position: [x, y, z] in meters
        orientation: [roll, pitch, yaw] in degrees (optional)
        workspace_bounds: Custom workspace bounds (optional)
        
    Returns:
        Tuple of (is_likely_reachable, reason)
    """
    if workspace_bounds is None:
        workspace_bounds = SAFE_WORKSPACE_BOUNDS
    
    x, y, z = position
    
    # Check position bounds
    if not (workspace_bounds['x'][0] <= x <= workspace_bounds['x'][1]):
        return False, f"X position {x:.3f}m outside safe range {workspace_bounds['x']}"
        
    if not (workspace_bounds['y'][0] <= y <= workspace_bounds['y'][1]):
        return False, f"Y position {y:.3f}m outside safe range {workspace_bounds['y']}"
        
    if not (workspace_bounds['z'][0] <= z <= workspace_bounds['z'][1]):
        return False, f"Z position {z:.3f}m outside safe range {workspace_bounds['z']}"
    
    # Check radial distance (approximate arm reach)
    radial_distance = np.sqrt(x**2 + y**2 + z**2)
    max_reach = 0.45  # Approximate maximum reach of SO-101 (increased)
    min_reach = 0.05  # Minimum reach (avoiding base collision)
    
    if radial_distance > max_reach:
        return False, f"Target too far: {radial_distance:.3f}m > {max_reach:.3f}m max reach"
        
    if radial_distance < min_reach:
        return False, f"Target too close: {radial_distance:.3f}m < {min_reach:.3f}m min reach"
    
    # Check orientation limits if provided
    if orientation is not None:
        roll, pitch, yaw = orientation
        
        if not (ORIENTATION_LIMITS['roll'][0] <= roll <= ORIENTATION_LIMITS['roll'][1]):
            return False, f"Roll {roll}° outside limits {ORIENTATION_LIMITS['roll']}"
            
        if not (ORIENTATION_LIMITS['pitch'][0] <= pitch <= ORIENTATION_LIMITS['pitch'][1]):
            return False, f"Pitch {pitch}° outside limits {ORIENTATION_LIMITS['pitch']}"
            
        if not (ORIENTATION_LIMITS['yaw'][0] <= yaw <= ORIENTATION_LIMITS['yaw'][1]):
            return False, f"Yaw {yaw}° outside limits {ORIENTATION_LIMITS['yaw']}"
    
    # Additional geometric checks
    
    # Check for ground collision
    if z < 0.02:
        return False, f"Z position {z:.3f}m too low (ground collision risk)"
    
    # Check for extreme lateral positions at low heights
    if z < 0.10 and abs(y) > 0.20:
        return False, f"Extreme lateral position {y:.3f}m at low height {z:.3f}m"
    
    # Check for extreme forward positions at low heights  
    if z < 0.08 and x > 0.30:
        return False, f"Extreme forward position {x:.3f}m at low height {z:.3f}m"
    
    return True, "Pose appears reachable"


def get_safe_workspace_bounds() -> Dict[str, Tuple[float, float]]:
    """Get conservative, tested workspace bounds for SO-101."""
    return SAFE_WORKSPACE_BOUNDS.copy()


def get_joint_limits() -> Dict[str, Tuple[float, float]]:
    """Get joint limits for SO-101 in degrees."""
    return JOINT_LIMITS.copy()


def get_orientation_limits() -> Dict[str, Tuple[float, float]]:
    """Get practical orientation limits in degrees."""
    return ORIENTATION_LIMITS.copy()


def suggest_safe_poses() -> Dict[str, Dict[str, List[float]]]:
    """Get a collection of tested, safe poses for different tasks."""
    return {
        'home_positions': {
            'neutral': [0.20, 0.00, 0.15],
            'ready': [0.25, 0.00, 0.20],
            'rest': [0.15, 0.00, 0.10],
        },
        'pickup_positions': {
            'low_pickup': [0.25, 0.10, 0.04],
            'table_pickup': [0.30, 0.15, 0.08],
            'elevated_pickup': [0.20, 0.05, 0.15],
        },
        'placement_positions': {
            'low_place': [0.30, -0.10, 0.06],
            'shelf_place': [0.25, -0.15, 0.20],
            'overhead_place': [0.15, 0.00, 0.30],
        },
        'demonstration_positions': {
            'wave_start': [0.20, 0.20, 0.25],
            'wave_end': [0.20, -0.20, 0.25],
            'point_forward': [0.35, 0.00, 0.15],
            'point_side': [0.20, 0.25, 0.15],
        }
    }


def validate_pose_sequence(poses: List[List[float]]) -> Tuple[bool, List[str]]:
    """
    Validate a sequence of poses for safety and reachability.
    
    Args:
        poses: List of [x, y, z] positions
        
    Returns:
        Tuple of (all_valid, list_of_issues)
    """
    issues = []
    
    for i, pose in enumerate(poses):
        is_safe, reason = quick_pose_check(pose)
        if not is_safe:
            issues.append(f"Pose {i+1} ({pose}): {reason}")
    
    # Check for large jumps between consecutive poses
    for i in range(len(poses) - 1):
        current = np.array(poses[i])
        next_pose = np.array(poses[i + 1])
        distance = np.linalg.norm(next_pose - current)
        
        if distance > 0.15:  # 15cm jump
            issues.append(f"Large jump from pose {i+1} to {i+2}: {distance:.3f}m")
    
    return len(issues) == 0, issues


def get_workspace_center() -> List[float]:
    """Get the approximate center of the workspace."""
    bounds = SAFE_WORKSPACE_BOUNDS
    return [
        (bounds['x'][0] + bounds['x'][1]) / 2,
        (bounds['y'][0] + bounds['y'][1]) / 2,
        (bounds['z'][0] + bounds['z'][1]) / 2,
    ]


def get_workspace_volume() -> float:
    """Calculate approximate workspace volume in cubic meters."""
    bounds = SAFE_WORKSPACE_BOUNDS
    volume = (
        (bounds['x'][1] - bounds['x'][0]) *
        (bounds['y'][1] - bounds['y'][0]) *
        (bounds['z'][1] - bounds['z'][0])
    )
    return volume


def distance_to_workspace_bounds(position: List[float]) -> Dict[str, float]:
    """
    Calculate distances to workspace boundaries.
    
    Returns:
        Dictionary with distances to each boundary (negative = outside)
    """
    x, y, z = position
    bounds = SAFE_WORKSPACE_BOUNDS
    
    return {
        'x_min': x - bounds['x'][0],
        'x_max': bounds['x'][1] - x,
        'y_min': y - bounds['y'][0], 
        'y_max': bounds['y'][1] - y,
        'z_min': z - bounds['z'][0],
        'z_max': bounds['z'][1] - z,
    }


def find_nearest_safe_pose(position: List[float]) -> Tuple[List[float], str]:
    """
    Find the nearest safe pose to a given position.
    
    Args:
        position: [x, y, z] target position
        
    Returns:
        Tuple of (nearest_safe_position, explanation)
    """
    x, y, z = position
    bounds = SAFE_WORKSPACE_BOUNDS
    
    # Clamp to workspace bounds
    safe_x = np.clip(x, bounds['x'][0], bounds['x'][1])
    safe_y = np.clip(y, bounds['y'][0], bounds['y'][1])
    safe_z = np.clip(z, bounds['z'][0], bounds['z'][1])
    
    safe_pose = [safe_x, safe_y, safe_z]
    
    # Check if we had to clamp
    changes = []
    if safe_x != x:
        changes.append(f"X: {x:.3f} → {safe_x:.3f}")
    if safe_y != y:
        changes.append(f"Y: {y:.3f} → {safe_y:.3f}")
    if safe_z != z:
        changes.append(f"Z: {z:.3f} → {safe_z:.3f}")
    
    if changes:
        explanation = f"Clamped to workspace bounds: {', '.join(changes)}"
    else:
        explanation = "Position was already within safe bounds"
    
    return safe_pose, explanation


def print_workspace_summary():
    """Print a summary of workspace characteristics."""
    bounds = SAFE_WORKSPACE_BOUNDS
    center = get_workspace_center()
    volume = get_workspace_volume()
    
    print("🤖 SO-101 Workspace Summary")
    print("=" * 40)
    print(f"X (Forward):  {bounds['x'][0]:.2f}m to {bounds['x'][1]:.2f}m")
    print(f"Y (Lateral):  {bounds['y'][0]:.2f}m to {bounds['y'][1]:.2f}m") 
    print(f"Z (Height):   {bounds['z'][0]:.2f}m to {bounds['z'][1]:.2f}m")
    print(f"Center:       [{center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f}]")
    print(f"Volume:       {volume:.4f} m³")
    print()
    print("🎯 Quick Usage:")
    print("   from workspace_check import quick_pose_check")
    print("   is_safe, reason = quick_pose_check([0.25, 0.15, 0.20])")
    print("   print(f'Safe: {is_safe} - {reason}')")


if __name__ == "__main__":
    print_workspace_summary()
    
    print("\n🧪 Testing Sample Poses:")
    test_poses = [
        ([0.20, 0.00, 0.15], "Home position"),
        ([0.35, 0.20, 0.25], "Extended reach"),
        ([0.50, 0.30, 0.10], "Too far out"),
        ([0.10, 0.00, 0.01], "Too low"),
        ([0.25, 0.15, 0.20], "Good working pose"),
    ]
    
    for pose, description in test_poses:
        is_safe, reason = quick_pose_check(pose)
        status = "✅" if is_safe else "❌"
        print(f"   {status} {description}: {pose} - {reason}")
    
    print("\n🎯 Safe Pose Categories:")
    safe_poses = suggest_safe_poses()
    for category, poses in safe_poses.items():
        print(f"\n   {category.replace('_', ' ').title()}:")
        for name, pose in poses.items():
            print(f"     {name}: {pose}")
