#!/usr/bin/env python3
"""
SO-101 Workspace Validator and Visualization Tool

This script provides utilities to:
1. Check if an end effector pose is reachable for the SO-101 arm
2. Visualize the workspace boundaries
3. Sample and map the reachable workspace
4. Validate poses before attempting to move the robot

Usage:
    python workspace_validator.py --check-pose 0.25 0.15 0.20
    python workspace_validator.py --sample-workspace
    python workspace_validator.py --visualize
"""

import argparse
import json
import time
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

try:
    from dual_so101_controller import DualSO101Controller
    CONTROLLER_AVAILABLE = True
except ImportError:
    CONTROLLER_AVAILABLE = False
    print("⚠️  DualSO101Controller not available. Running in standalone mode.")


class SO101WorkspaceValidator:
    """Validates and analyzes SO-101 workspace reachability."""
    
    def __init__(self, arm_side: str = "left"):
        """
        Initialize workspace validator.
        
        Args:
            arm_side: Which arm to analyze ("left" or "right")
        """
        self.arm_side = arm_side
        
        if CONTROLLER_AVAILABLE:
            self.controller = DualSO101Controller(simulation_mode=True)
        else:
            self.controller = None
            print(f"⚠️  Running without robot controller - basic validation only")
        
        # Approximate workspace bounds for SO-101 (in meters)
        # These are conservative estimates based on arm geometry
        self.workspace_bounds = {
            'x': (0.05, 0.40),    # Forward reach: 5cm to 40cm
            'y': (-0.30, 0.30),   # Side reach: ±30cm
            'z': (0.02, 0.35),    # Height: 2cm to 35cm
        }
        
        # IK validation thresholds
        self.position_tolerance = 0.005  # 5mm precision
        self.orientation_tolerance = 0.1  # ~5.7 degrees
        
    def check_pose_reachability(
        self, 
        position: List[float], 
        orientation: Optional[List[float]] = None,
        verbose: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if a pose is reachable by the SO-101 arm.
        
        Args:
            position: [x, y, z] in meters
            orientation: [roll, pitch, yaw] in degrees (optional)
            verbose: Print detailed results
            
        Returns:
            Tuple of (is_reachable, reason, validation_data)
        """
        if orientation is None:
            orientation = [0, 0, 0]  # Default orientation
            
        x, y, z = position
        roll, pitch, yaw = orientation
        
        validation_data = {
            'target_position': position,
            'target_orientation': orientation,
            'timestamp': time.time(),
        }
        
        # 1. Check basic workspace bounds
        if not (self.workspace_bounds['x'][0] <= x <= self.workspace_bounds['x'][1]):
            reason = f"X position {x:.3f}m outside workspace bounds {self.workspace_bounds['x']}"
            return False, reason, validation_data
            
        if not (self.workspace_bounds['y'][0] <= y <= self.workspace_bounds['y'][1]):
            reason = f"Y position {y:.3f}m outside workspace bounds {self.workspace_bounds['y']}"
            return False, reason, validation_data
            
        if not (self.workspace_bounds['z'][0] <= z <= self.workspace_bounds['z'][1]):
            reason = f"Z position {z:.3f}m outside workspace bounds {self.workspace_bounds['z']}"
            return False, reason, validation_data
        
        # 2. Check orientation limits (practical limits for SO-101)
        if abs(roll) > 90 or abs(pitch) > 90 or abs(yaw) > 180:
            reason = f"Orientation {orientation} exceeds practical limits (±90° roll/pitch, ±180° yaw)"
            return False, reason, validation_data
        
        # 3. Test inverse kinematics (if controller available)
        if self.controller is None:
            # Fallback to geometric validation only
            if verbose:
                print(f"✅ Pose passes basic validation (IK not available)")
            return True, "Pose passes basic geometric validation", validation_data
        
        try:
            # Get current joint positions as starting point
            arm = getattr(self.controller, f"{self.arm_side}_arm")
            current_joints = arm.read_joints_position(unit="rad", source="simulation")
            
            # Attempt IK
            target_joints = arm.inverse_kinematics(
                target_position_cartesian=np.array(position),
                target_orientation_quaternions=self._euler_to_quaternion(roll, pitch, yaw)
            )
            
            validation_data['ik_solution'] = target_joints.tolist()
            
            # 4. Verify IK solution by forward kinematics
            # Set the joints in simulation
            arm.sim.set_joints_states(
                robot_id=arm.p_robot_id,
                joint_indices=arm.actuated_joints,
                target_positions=target_joints.tolist()
            )
            arm.sim.step()
            
            # Get actual end effector pose
            actual_pos, actual_orient = arm.forward_kinematics(sync_robot_pos=False)
            
            validation_data['actual_position'] = actual_pos.tolist()
            validation_data['actual_orientation'] = actual_orient.tolist()
            
            # Check position accuracy
            pos_error = np.linalg.norm(np.array(position) - actual_pos)
            validation_data['position_error'] = float(pos_error)
            
            if pos_error > self.position_tolerance:
                reason = f"IK solution inaccurate: {pos_error*1000:.1f}mm error (tolerance: {self.position_tolerance*1000:.1f}mm)"
                return False, reason, validation_data
            
            # Check orientation accuracy (if specified)
            if orientation != [0, 0, 0]:
                target_quat = self._euler_to_quaternion(roll, pitch, yaw)
                orient_error = self._quaternion_angle_difference(target_quat, actual_orient)
                validation_data['orientation_error'] = float(orient_error)
                
                if orient_error > self.orientation_tolerance:
                    reason = f"Orientation error: {np.degrees(orient_error):.1f}° (tolerance: {np.degrees(self.orientation_tolerance):.1f}°)"
                    return False, reason, validation_data
            
            # 5. Check for joint limits violation
            joint_limits_ok = True
            for i, (joint_pos, lower, upper) in enumerate(zip(
                target_joints, arm.lower_joint_limits, arm.upper_joint_limits
            )):
                if not (lower <= joint_pos <= upper):
                    reason = f"Joint {i+1} ({joint_pos:.3f} rad) violates limits [{lower:.3f}, {upper:.3f}]"
                    validation_data['joint_limit_violation'] = {
                        'joint_index': i,
                        'value': float(joint_pos),
                        'limits': [float(lower), float(upper)]
                    }
                    return False, reason, validation_data
            
            # Success!
            if verbose:
                print(f"✅ Pose reachable with {pos_error*1000:.1f}mm precision")
                
            return True, "Pose is reachable", validation_data
            
        except Exception as e:
            reason = f"IK computation failed: {str(e)}"
            validation_data['error'] = str(e)
            return False, reason, validation_data
    
    def sample_workspace(
        self, 
        grid_resolution: int = 20,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        Sample the workspace to map reachable vs unreachable regions.
        
        Args:
            grid_resolution: Number of points per dimension
            save_results: Save results to JSON file
            
        Returns:
            Dictionary with sampling results
        """
        print(f"🔍 Sampling {self.arm_side} arm workspace...")
        print(f"   Grid resolution: {grid_resolution}³ = {grid_resolution**3:,} points")
        
        # Create sampling grid
        x_points = np.linspace(
            self.workspace_bounds['x'][0], 
            self.workspace_bounds['x'][1], 
            grid_resolution
        )
        y_points = np.linspace(
            self.workspace_bounds['y'][0], 
            self.workspace_bounds['y'][1], 
            grid_resolution
        )
        z_points = np.linspace(
            self.workspace_bounds['z'][0], 
            self.workspace_bounds['z'][1], 
            grid_resolution
        )
        
        results = {
            'arm_side': self.arm_side,
            'grid_resolution': grid_resolution,
            'workspace_bounds': self.workspace_bounds,
            'reachable_points': [],
            'unreachable_points': [],
            'reachable_count': 0,
            'total_points': grid_resolution ** 3,
            'sampling_time': time.time()
        }
        
        count = 0
        start_time = time.time()
        
        for i, x in enumerate(x_points):
            for j, y in enumerate(y_points):
                for k, z in enumerate(z_points):
                    count += 1
                    position = [x, y, z]
                    
                    # Check reachability (without verbose output)
                    is_reachable, reason, data = self.check_pose_reachability(
                        position, verbose=False
                    )
                    
                    point_data = {
                        'position': position,
                        'reachable': is_reachable,
                        'reason': reason if not is_reachable else None
                    }
                    
                    if is_reachable:
                        results['reachable_points'].append(point_data)
                        results['reachable_count'] += 1
                    else:
                        results['unreachable_points'].append(point_data)
                    
                    # Progress update
                    if count % 1000 == 0:
                        elapsed = time.time() - start_time
                        progress = count / results['total_points']
                        eta = elapsed / progress - elapsed if progress > 0 else 0
                        print(f"   Progress: {count:,}/{results['total_points']:,} "
                              f"({progress*100:.1f}%) - ETA: {eta:.0f}s")
        
        results['reachable_percentage'] = (results['reachable_count'] / results['total_points']) * 100
        results['sampling_duration'] = time.time() - start_time
        
        print(f"\n📊 Workspace Sampling Results:")
        print(f"   Reachable points: {results['reachable_count']:,}/{results['total_points']:,} "
              f"({results['reachable_percentage']:.1f}%)")
        print(f"   Sampling time: {results['sampling_duration']:.1f}s")
        
        if save_results:
            filename = f"workspace_sample_{self.arm_side}_{grid_resolution}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"   Results saved to: {filename}")
        
        return results
    
    def visualize_workspace(
        self, 
        sample_data: Optional[Dict] = None,
        sample_file: Optional[str] = None
    ):
        """
        Create 3D visualization of the workspace.
        
        Args:
            sample_data: Pre-computed sampling data
            sample_file: Path to JSON file with sampling data
        """
        # Load sample data
        if sample_data is None:
            if sample_file:
                with open(sample_file, 'r') as f:
                    sample_data = json.load(f)
            else:
                print("⚠️  No sample data provided. Running quick sampling...")
                sample_data = self.sample_workspace(grid_resolution=10, save_results=False)
        
        # Extract points
        reachable_points = np.array([p['position'] for p in sample_data['reachable_points']])
        unreachable_points = np.array([p['position'] for p in sample_data['unreachable_points']])
        
        # Create 3D plot
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot reachable points
        if len(reachable_points) > 0:
            ax.scatter(
                reachable_points[:, 0], 
                reachable_points[:, 1], 
                reachable_points[:, 2],
                c='green', alpha=0.6, s=10, label='Reachable'
            )
        
        # Plot unreachable points
        if len(unreachable_points) > 0:
            ax.scatter(
                unreachable_points[:, 0], 
                unreachable_points[:, 1], 
                unreachable_points[:, 2],
                c='red', alpha=0.3, s=5, label='Unreachable'
            )
        
        # Set labels and title
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Z (m)')
        ax.set_title(f'SO-101 {sample_data["arm_side"].title()} Arm Workspace\n'
                    f'{sample_data["reachable_count"]:,}/{sample_data["total_points"]:,} '
                    f'reachable ({sample_data.get("reachable_percentage", 0):.1f}%)')
        ax.legend()
        
        # Set equal aspect ratio
        max_range = 0.2
        ax.set_xlim(0, max_range*2)
        ax.set_ylim(-max_range, max_range)
        ax.set_zlim(0, max_range*1.5)
        
        plt.tight_layout()
        plt.show()
    
    def get_workspace_summary(self) -> Dict[str, Any]:
        """Get a summary of workspace characteristics."""
        return {
            'arm_side': self.arm_side,
            'workspace_bounds': self.workspace_bounds,
            'position_tolerance': self.position_tolerance,
            'orientation_tolerance': self.orientation_tolerance,
            'approximate_reach': {
                'max_forward': self.workspace_bounds['x'][1],
                'max_lateral': max(abs(self.workspace_bounds['y'][0]), 
                                abs(self.workspace_bounds['y'][1])),
                'max_height': self.workspace_bounds['z'][1],
                'min_height': self.workspace_bounds['z'][0],
            },
            'typical_poses': {
                'home': [0.20, 0.00, 0.15],
                'extended': [0.35, 0.10, 0.20],
                'pickup': [0.25, 0.15, 0.05],
                'overhead': [0.15, 0.00, 0.30],
            }
        }
    
    def _euler_to_quaternion(self, roll: float, pitch: float, yaw: float) -> np.ndarray:
        """Convert Euler angles (degrees) to quaternion."""
        r, p, y = np.radians([roll, pitch, yaw])
        
        cy = np.cos(y * 0.5)
        sy = np.sin(y * 0.5)
        cp = np.cos(p * 0.5)
        sp = np.sin(p * 0.5)
        cr = np.cos(r * 0.5)
        sr = np.sin(r * 0.5)
        
        qw = cr * cp * cy + sr * sp * sy
        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy
        
        return np.array([qx, qy, qz, qw])
    
    def _quaternion_angle_difference(self, q1: np.ndarray, q2: np.ndarray) -> float:
        """Calculate angular difference between two quaternions."""
        # Normalize quaternions
        q1 = q1 / np.linalg.norm(q1)
        q2 = q2 / np.linalg.norm(q2)
        
        # Calculate dot product
        dot = np.abs(np.dot(q1, q2))
        dot = np.clip(dot, 0.0, 1.0)
        
        # Return angle difference
        return 2 * np.arccos(dot)


def main():
    """Command line interface for workspace validation."""
    parser = argparse.ArgumentParser(
        description="SO-101 Workspace Validator and Visualization Tool"
    )
    parser.add_argument(
        '--arm', choices=['left', 'right'], default='left',
        help='Which arm to analyze (default: left)'
    )
    parser.add_argument(
        '--check-pose', nargs=3, type=float, metavar=('X', 'Y', 'Z'),
        help='Check if a specific pose [x y z] is reachable (in meters)'
    )
    parser.add_argument(
        '--check-pose-orient', nargs=6, type=float, 
        metavar=('X', 'Y', 'Z', 'ROLL', 'PITCH', 'YAW'),
        help='Check pose with orientation [x y z roll pitch yaw] (meters, degrees)'
    )
    parser.add_argument(
        '--sample-workspace', action='store_true',
        help='Sample the workspace to map reachable regions'
    )
    parser.add_argument(
        '--resolution', type=int, default=15,
        help='Grid resolution for workspace sampling (default: 15)'
    )
    parser.add_argument(
        '--visualize', action='store_true',
        help='Visualize the workspace (requires sampling data)'
    )
    parser.add_argument(
        '--load-sample', type=str,
        help='Load existing sample data from JSON file'
    )
    parser.add_argument(
        '--summary', action='store_true',
        help='Show workspace summary information'
    )
    
    args = parser.parse_args()
    
    # Initialize validator
    print(f"🤖 Initializing SO-101 {args.arm} arm workspace validator...")
    validator = SO101WorkspaceValidator(arm_side=args.arm)
    
    try:
        # Handle different commands
        if args.check_pose:
            print(f"\n🎯 Checking pose reachability: {args.check_pose}")
            is_reachable, reason, data = validator.check_pose_reachability(args.check_pose)
            
            if is_reachable:
                print(f"✅ {reason}")
                print(f"   Position error: {data['position_error']*1000:.2f}mm")
            else:
                print(f"❌ {reason}")
        
        elif args.check_pose_orient:
            position = args.check_pose_orient[:3]
            orientation = args.check_pose_orient[3:]
            print(f"\n🎯 Checking pose with orientation:")
            print(f"   Position: {position}")
            print(f"   Orientation: {orientation}° (roll, pitch, yaw)")
            
            is_reachable, reason, data = validator.check_pose_reachability(
                position, orientation
            )
            
            if is_reachable:
                print(f"✅ {reason}")
                print(f"   Position error: {data['position_error']*1000:.2f}mm")
                if 'orientation_error' in data:
                    print(f"   Orientation error: {np.degrees(data['orientation_error']):.2f}°")
            else:
                print(f"❌ {reason}")
        
        elif args.sample_workspace:
            sample_data = validator.sample_workspace(grid_resolution=args.resolution)
        
        elif args.visualize:
            if args.load_sample:
                validator.visualize_workspace(sample_file=args.load_sample)
            else:
                # Look for existing sample file
                import glob
                sample_files = glob.glob(f"workspace_sample_{args.arm}_*.json")
                if sample_files:
                    latest_file = max(sample_files, key=lambda x: int(x.split('_')[-1].split('.')[0]))
                    print(f"📁 Loading existing sample data: {latest_file}")
                    validator.visualize_workspace(sample_file=latest_file)
                else:
                    print("⚠️  No existing sample data found. Run --sample-workspace first.")
        
        elif args.summary:
            summary = validator.get_workspace_summary()
            print(f"\n📋 SO-101 {summary['arm_side'].title()} Arm Workspace Summary:")
            print(f"   Max forward reach: {summary['approximate_reach']['max_forward']:.2f}m")
            print(f"   Max lateral reach: ±{summary['approximate_reach']['max_lateral']:.2f}m")
            print(f"   Height range: {summary['approximate_reach']['min_height']:.2f}m to {summary['approximate_reach']['max_height']:.2f}m")
            print(f"   Position tolerance: {summary['position_tolerance']*1000:.1f}mm")
            print(f"   Orientation tolerance: {np.degrees(summary['orientation_tolerance']):.1f}°")
            
            print(f"\n🎯 Typical Reachable Poses:")
            for name, pos in summary['typical_poses'].items():
                print(f"   {name.capitalize()}: {pos}")
        
        else:
            parser.print_help()
            print(f"\nExample usage:")
            print(f"  python workspace_validator.py --check-pose 0.25 0.15 0.20")
            print(f"  python workspace_validator.py --sample-workspace --resolution 20")
            print(f"  python workspace_validator.py --visualize")
            print(f"  python workspace_validator.py --summary")
    
    finally:
        # Cleanup
        validator.controller.disconnect()


if __name__ == "__main__":
    main()
