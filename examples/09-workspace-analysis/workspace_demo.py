#!/usr/bin/env python3
"""
Workspace Validation Demo for SO-101

This script demonstrates how to check for forbidden poses and
understand the workspace limits of the SO-101 robotic arm.

Run this script to see practical examples of:
- Pose validation
- Workspace boundary checks  
- Safe pose suggestions
- Common forbidden pose scenarios
"""

import time
from workspace_check import (
    quick_pose_check, 
    find_nearest_safe_pose,
    get_safe_workspace_bounds,
    suggest_safe_poses,
    validate_pose_sequence,
    print_workspace_summary
)


def demo_basic_validation():
    """Demonstrate basic pose validation."""
    print("\n🎯 Basic Pose Validation Demo")
    print("=" * 40)
    
    test_poses = [
        # Format: ([x, y, z], "description") 
        ([0.20, 0.10, 0.15], "Safe home position"),
        ([0.30, 0.15, 0.25], "Good working pose"),
        ([0.35, 0.25, 0.30], "Near workspace edge"),
        ([0.45, 0.20, 0.15], "Too far forward"),
        ([0.25, 0.35, 0.20], "Too far lateral"),
        ([0.20, 0.10, 0.01], "Too low (ground risk)"),
        ([0.05, 0.00, 0.10], "Too close to base"),
    ]
    
    for position, description in test_poses:
        is_safe, reason = quick_pose_check(position)
        status = "✅" if is_safe else "❌"
        print(f"{status} {description}")
        print(f"   Position: {position}")
        print(f"   Result: {reason}")
        
        # If unsafe, show safe alternative
        if not is_safe:
            safe_pose, explanation = find_nearest_safe_pose(position)
            print(f"   💡 Safe alternative: {safe_pose}")
            print(f"      {explanation}")
        print()


def demo_orientation_limits():
    """Demonstrate orientation validation."""
    print("\n🔄 Orientation Limits Demo")
    print("=" * 35)
    
    base_position = [0.25, 0.15, 0.20]  # Safe position
    
    test_orientations = [
        # Format: ([roll, pitch, yaw], "description")
        ([0, 0, 0], "Neutral orientation"),
        ([0, 45, 0], "45° pitch down"),
        ([30, 0, -45], "30° roll, -45° yaw"),
        ([90, 0, 0], "90° roll (limit)"),
        ([120, 0, 0], "Excessive roll"),
        ([0, 100, 0], "Excessive pitch"),
        ([0, 0, 200], "Excessive yaw"),
    ]
    
    for orientation, description in test_orientations:
        is_safe, reason = quick_pose_check(base_position, orientation)
        status = "✅" if is_safe else "❌"
        print(f"{status} {description}")
        print(f"   Orientation: {orientation}° (roll, pitch, yaw)")
        print(f"   Result: {reason}")
        print()


def demo_trajectory_validation():
    """Demonstrate trajectory validation."""
    print("\n🛤️  Trajectory Validation Demo")
    print("=" * 37)
    
    trajectories = {
        "Safe trajectory": [
            [0.20, 0.10, 0.15],  # Start
            [0.25, 0.15, 0.20],  # Middle  
            [0.30, 0.10, 0.25],  # End
        ],
        "Trajectory with large jump": [
            [0.20, 0.10, 0.15],  # Start
            [0.35, 0.25, 0.30],  # Large jump
            [0.25, 0.15, 0.20],  # End
        ],
        "Trajectory with forbidden pose": [
            [0.20, 0.10, 0.15],  # Start
            [0.45, 0.30, 0.35],  # Forbidden pose
            [0.30, 0.20, 0.25],  # End
        ]
    }
    
    for name, waypoints in trajectories.items():
        print(f"Testing: {name}")
        is_valid, issues = validate_pose_sequence(waypoints)
        
        if is_valid:
            print("   ✅ Trajectory is valid")
        else:
            print("   ❌ Trajectory has issues:")
            for issue in issues:
                print(f"      • {issue}")
        
        print(f"   Waypoints: {len(waypoints)}")
        for i, waypoint in enumerate(waypoints):
            print(f"     {i+1}. {waypoint}")
        print()


def demo_workspace_boundaries():
    """Demonstrate workspace boundary analysis."""
    print("\n📏 Workspace Boundaries Demo")
    print("=" * 36)
    
    bounds = get_safe_workspace_bounds()
    
    print("Safe workspace bounds:")
    for axis, (min_val, max_val) in bounds.items():
        print(f"   {axis.upper()}: {min_val:.2f}m to {max_val:.2f}m")
    
    print("\nTesting boundary positions:")
    
    # Test positions at boundaries
    boundary_tests = [
        ([bounds['x'][0], 0.00, 0.15], "X minimum"),
        ([bounds['x'][1], 0.00, 0.15], "X maximum"),
        ([0.25, bounds['y'][0], 0.15], "Y minimum"),
        ([0.25, bounds['y'][1], 0.15], "Y maximum"),
        ([0.25, 0.00, bounds['z'][0]], "Z minimum"),
        ([0.25, 0.00, bounds['z'][1]], "Z maximum"),
    ]
    
    for position, description in boundary_tests:
        is_safe, reason = quick_pose_check(position)
        status = "✅" if is_safe else "❌"
        print(f"   {status} {description}: {position} - {reason}")


def demo_safe_pose_categories():
    """Demonstrate categorized safe poses."""
    print("\n🎭 Safe Pose Categories Demo")
    print("=" * 34)
    
    safe_poses = suggest_safe_poses()
    
    for category, poses in safe_poses.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for name, position in poses.items():
            # Validate each suggested pose
            is_safe, reason = quick_pose_check(position)
            status = "✅" if is_safe else "❌"
            print(f"   {status} {name}: {position}")
            if not is_safe:
                print(f"       ⚠️  {reason}")


def demo_practical_scenarios():
    """Demonstrate practical usage scenarios."""
    print("\n🔧 Practical Scenarios Demo")
    print("=" * 32)
    
    scenarios = {
        "Pick object from table": {
            "approach": [0.25, 0.15, 0.15],
            "grasp": [0.25, 0.15, 0.05],
            "lift": [0.25, 0.15, 0.20],
        },
        "Place object on shelf": {
            "approach": [0.20, -0.10, 0.20],
            "place": [0.20, -0.10, 0.25],
            "retract": [0.20, -0.10, 0.20],
        },
        "Handoff between arms": {
            "left_ready": [0.20, 0.05, 0.18],
            "right_ready": [0.20, -0.05, 0.18],
            "center": [0.20, 0.00, 0.18],
        }
    }
    
    for scenario_name, poses in scenarios.items():
        print(f"\nScenario: {scenario_name}")
        
        pose_list = list(poses.values())
        is_valid, issues = validate_pose_sequence(pose_list)
        
        if is_valid:
            print("   ✅ All poses in scenario are valid")
        else:
            print("   ⚠️  Scenario has issues:")
            for issue in issues:
                print(f"      • {issue}")
        
        for step_name, position in poses.items():
            is_safe, reason = quick_pose_check(position)
            status = "✅" if is_safe else "❌"
            print(f"   {status} {step_name}: {position}")


def main():
    """Run all workspace validation demos."""
    print("🤖 SO-101 Workspace Validation Demo")
    print("===================================")
    
    # Show workspace summary
    print_workspace_summary()
    
    # Run demonstration modules
    demo_basic_validation()
    demo_orientation_limits()
    demo_trajectory_validation()
    demo_workspace_boundaries()
    demo_safe_pose_categories()
    demo_practical_scenarios()
    
    print("\n🎓 Demo Complete!")
    print("Key Takeaways:")
    print("• Always validate poses before sending to robot")
    print("• Use quick_pose_check() for fast validation")
    print("• Use find_nearest_safe_pose() for corrections")
    print("• Validate entire trajectories with validate_pose_sequence()")
    print("• Stay within conservative workspace bounds for reliability")
    print("• Test orientation limits carefully (±90° roll/pitch recommended)")
    
    print("\n🔧 Next Steps:")
    print("• Try: python workspace_validator.py --check-pose 0.25 0.15 0.20")
    print("• Try: python workspace_validator.py --sample-workspace") 
    print("• Try: python workspace_validator.py --visualize")
    print("• Integrate validation into your control scripts")


if __name__ == "__main__":
    main()
