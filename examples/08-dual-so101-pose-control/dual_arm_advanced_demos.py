#!/usr/bin/env python3
"""
🤖 Dual Arm Advanced Demos Suite
===============================

Comprehensive demonstrations of advanced dual-arm coordination and choreographed movements.
Consolidates coordination patterns, dance sequences, and synchronized movement demos.

Usage:
    python3 dual_arm_advanced_demos.py                    # Run all demos
    python3 dual_arm_advanced_demos.py --coordination     # Coordination patterns only
    python3 dual_arm_advanced_demos.py --dance            # Dance sequences only
    python3 dual_arm_advanced_demos.py --mirror           # Mirror movements only
    python3 dual_arm_advanced_demos.py --handoff          # Handoff simulations only
"""

import time
import sys
import threading
import numpy as np
from dual_so101_controller import DualSO101Controller


class DualArmCoordinator:
    """Coordinator for synchronized dual-arm movements and advanced demos."""
    
    # Common end effector pose presets (position in meters, orientation in degrees)
    POSES = {
        'safe_left': {'position': [0.25, 0.15, 0.25], 'orientation': [0, 0, 0]},
        'safe_right': {'position': [0.25, -0.15, 0.25], 'orientation': [0, 0, 0]},
        'home_left': {'position': [0.20, 0.10, 0.18], 'orientation': [0, 0, -15]},
        'home_right': {'position': [0.20, -0.10, 0.18], 'orientation': [0, 0, 15]},
        'pickup_left': {'position': [0.30, 0.12, 0.12], 'orientation': [0, 45, 0]},
        'pickup_right': {'position': [0.30, -0.12, 0.12], 'orientation': [0, 45, 0]},
        'handoff_left': {'position': [0.20, 0.05, 0.18], 'orientation': [0, 0, 45]},
        'handoff_right': {'position': [0.20, -0.05, 0.18], 'orientation': [0, 0, -45]},
        'wave_up_left': {'position': [0.25, 0.20, 0.30], 'orientation': [0, 0, -30]},
        'wave_up_right': {'position': [0.25, -0.20, 0.30], 'orientation': [0, 0, 30]},
        'wave_down_left': {'position': [0.25, 0.20, 0.15], 'orientation': [0, 0, 30]},
        'wave_down_right': {'position': [0.25, -0.20, 0.15], 'orientation': [0, 0, -30]},
    }
    
    def __init__(self, controller: DualSO101Controller):
        self.controller = controller
    
    def synchronized_movement(self, 
                            left_pose: list[float], 
                            right_pose: list[float],
                            left_orientation: list[float] = None,
                            right_orientation: list[float] = None):
        """Move both arm end effectors simultaneously to specified poses."""
        
        def move_left():
            try:
                self.controller.move_arm_absolute_pose(
                    robot_id=0, 
                    position=left_pose,
                    orientation=left_orientation
                )
                print("✅ Left arm movement completed")
            except Exception as e:
                print(f"❌ Left arm movement failed: {e}")
        
        def move_right():
            try:
                self.controller.move_arm_absolute_pose(
                    robot_id=1,
                    position=right_pose,
                    orientation=right_orientation
                )
                print("✅ Right arm movement completed")
            except Exception as e:
                print(f"❌ Right arm movement failed: {e}")
                print("💡 This may fail if only one robot is connected")
        
        # Start movements in parallel
        left_thread = threading.Thread(target=move_left)
        right_thread = threading.Thread(target=move_right)
        
        print(f"🤝 Synchronizing movement: Left→{left_pose}, Right→{right_pose}")
        
        left_thread.start()
        right_thread.start()
        
        # Wait for both to complete
        left_thread.join()
        right_thread.join()
        
        print("✅ Synchronized movement completed!")
    
    def mirror_movement(self, center_pose: list[float], offset: float = 0.15):
        """Move arms to mirror positions around a center point."""
        left_pose = [center_pose[0], center_pose[1] + offset, center_pose[2]]
        right_pose = [center_pose[0], center_pose[1] - offset, center_pose[2]]
        
        # Mirror orientations (rotate wrists inward)
        left_orientation = [0, 0, -15]
        right_orientation = [0, 0, 15]
        
        print(f"🪞 Mirror movement around center {center_pose}")
        self.synchronized_movement(left_pose, right_pose, left_orientation, right_orientation)
    
    def coordination_demo(self):
        """Demonstrate various coordination patterns."""
        print("\n" + "="*60)
        print("🤝 DUAL ARM COORDINATION DEMO")
        print("="*60)
        
        try:
            # Pattern 1: Mirror movements
            print("\n🪞 Pattern 1: Mirror Movements")
            print("Moving arms to mirrored positions...")
            
            centers = [
                [0.25, 0.0, 0.20],  # Center low
                [0.25, 0.0, 0.25],  # Center high
                [0.30, 0.0, 0.22],  # Forward center
                [0.20, 0.0, 0.22],  # Back center
            ]
            
            for i, center in enumerate(centers):
                print(f"  Mirror position {i+1}/4: {center}")
                self.mirror_movement(center)
                time.sleep(2)
            
            # Pattern 2: Synchronized gripper control
            print("\n🤏 Pattern 2: Synchronized Gripper Control")
            print("Coordinating gripper movements...")
            
            # Open both grippers
            print("  Opening both grippers...")
            self.controller.control_gripper(0, 1.0)
            self.controller.control_gripper(1, 1.0)
            time.sleep(1)
            
            # Close both grippers
            print("  Closing both grippers...")
            self.controller.control_gripper(0, 0.0)
            self.controller.control_gripper(1, 0.0)
            time.sleep(1)
            
            # Alternating gripper control
            print("  Alternating gripper control...")
            for i in range(3):
                print(f"    Round {i+1}: Left open, right closed")
                self.controller.control_gripper(0, 1.0)
                self.controller.control_gripper(1, 0.0)
                time.sleep(0.8)
                
                print(f"    Round {i+1}: Left closed, right open")
                self.controller.control_gripper(0, 0.0)
                self.controller.control_gripper(1, 1.0)
                time.sleep(0.8)
            
            # Pattern 3: Coordinated workspace exploration
            print("\n🌐 Pattern 3: Coordinated Workspace Exploration")
            print("Exploring workspace boundaries together...")
            
            exploration_points = [
                ([0.30, 0.15, 0.25], [0.30, -0.15, 0.25]),  # Forward positions
                ([0.20, 0.15, 0.25], [0.20, -0.15, 0.25]),  # Back positions
                ([0.25, 0.20, 0.25], [0.25, -0.20, 0.25]),  # Wide positions
                ([0.25, 0.10, 0.30], [0.25, -0.10, 0.30]),  # High positions
                ([0.25, 0.10, 0.15], [0.25, -0.10, 0.15]),  # Low positions
            ]
            
            for i, (left_pos, right_pos) in enumerate(exploration_points):
                print(f"  Exploration point {i+1}/5: {left_pos} | {right_pos}")
                self.synchronized_movement(left_pos, right_pos)
                time.sleep(1.5)
            
            print("\n✅ Coordination demo completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Coordination demo failed: {e}")
            return False

    def dance_sequence_wave(self):
        """Wave motion with both arms."""
        print("\n🎭 Dance Sequence: Synchronized Wave")
        
        try:
            wave_positions = [
                # Starting low
                ([0.25, 0.15, 0.18], [0.25, -0.15, 0.18]),
                # Rising up
                ([0.25, 0.18, 0.25], [0.25, -0.18, 0.25]),
                # Peak wave
                ([0.25, 0.20, 0.30], [0.25, -0.20, 0.30]),
                # Coming down
                ([0.25, 0.18, 0.22], [0.25, -0.18, 0.22]),
                # Back to start
                ([0.25, 0.15, 0.18], [0.25, -0.15, 0.18]),
            ]
            
            for i, (left_pos, right_pos) in enumerate(wave_positions):
                print(f"  Wave motion {i+1}/5...")
                self.synchronized_movement(left_pos, right_pos)
                time.sleep(1.2)
            
            print("✅ Wave sequence completed!")
            return True
            
        except Exception as e:
            print(f"❌ Wave sequence failed: {e}")
            return False

    def dance_sequence_alternating(self):
        """Alternating arm dance movements."""
        print("\n🕺 Dance Sequence: Alternating Arms")
        
        try:
            # Start in sync
            self.synchronized_movement([0.25, 0.15, 0.20], [0.25, -0.15, 0.20])
            time.sleep(1)
            
            # Alternating up/down movements
            for i in range(4):
                print(f"  Alternating movement {i+1}/4...")
                
                # Left up, right down
                self.synchronized_movement([0.25, 0.15, 0.28], [0.25, -0.15, 0.15])
                time.sleep(0.8)
                
                # Right up, left down  
                self.synchronized_movement([0.25, 0.15, 0.15], [0.25, -0.15, 0.28])
                time.sleep(0.8)
            
            # Return to sync
            self.synchronized_movement([0.25, 0.15, 0.20], [0.25, -0.15, 0.20])
            
            print("✅ Alternating sequence completed!")
            return True
            
        except Exception as e:
            print(f"❌ Alternating sequence failed: {e}")
            return False

    def dance_sequence_circle(self):
        """Circular motion dance pattern."""
        print("\n🌀 Dance Sequence: Circular Motion")
        
        try:
            # Create circular path points
            center_x, center_y, center_z = 0.25, 0.0, 0.22
            radius = 0.08
            num_points = 8
            
            for i in range(num_points):
                angle = (2 * np.pi * i) / num_points
                
                # Left arm: clockwise circle
                left_y = center_y + 0.15 + radius * np.cos(angle)
                left_z = center_z + radius * np.sin(angle)
                
                # Right arm: counter-clockwise circle
                right_y = center_y - 0.15 - radius * np.cos(angle)
                right_z = center_z - radius * np.sin(angle)
                
                print(f"  Circle motion {i+1}/{num_points}...")
                self.synchronized_movement([center_x, left_y, left_z], [center_x, right_y, right_z])
                time.sleep(0.6)
            
            print("✅ Circle sequence completed!")
            return True
            
        except Exception as e:
            print(f"❌ Circle sequence failed: {e}")
            return False

    def dance_demo(self):
        """Complete choreographed dance demonstration."""
        print("\n" + "="*60)
        print("💃 DUAL ARM DANCE DEMO")
        print("="*60)
        print("Choreographed sequence showcasing dual-arm coordination!")
        
        try:
            # Initialize to starting position
            print("\n🎬 Initializing dance positions...")
            self.synchronized_movement([0.25, 0.15, 0.20], [0.25, -0.15, 0.20])
            time.sleep(2)
            
            # Sequence 1: Wave
            success1 = self.dance_sequence_wave()
            time.sleep(1)
            
            # Sequence 2: Alternating
            success2 = self.dance_sequence_alternating()
            time.sleep(1)
            
            # Sequence 3: Circle
            success3 = self.dance_sequence_circle()
            time.sleep(1)
            
            # Finale: Return to safe position
            print("\n🏠 Dance finale - returning to safe positions...")
            self.synchronized_movement([0.25, 0.15, 0.25], [0.25, -0.15, 0.25])
            
            print("\n" + "="*60)
            print("🎊 DANCE DEMO COMPLETE!")
            print("="*60)
            
            if success1 and success2 and success3:
                print("✅ All dance sequences executed successfully!")
                print("🤖 Dual SO-101 robots performed a complete choreographed routine!")
                return True
            else:
                print("⚠️ Some dance sequences had issues")
                return False
                
        except Exception as e:
            print(f"❌ Dance demo failed: {e}")
            return False

    def handoff_simulation(self):
        """Simulate object handoff between arms."""
        print("\n" + "="*60)
        print("🤝 HANDOFF SIMULATION DEMO")
        print("="*60)
        
        try:
            # Start positions
            print("\n📍 Setting up handoff positions...")
            self.synchronized_movement([0.25, 0.15, 0.20], [0.25, -0.15, 0.20])
            time.sleep(2)
            
            # Phase 1: Left arm "picks up" object
            print("\n📦 Phase 1: Left arm picks up object")
            print("  Moving left arm to pickup position...")
            self.controller.move_arm_absolute_pose(0, [0.30, 0.12, 0.12], [0, 45, 0])
            time.sleep(2)
            
            print("  Closing left gripper (grabbing object)...")
            self.controller.control_gripper(0, 0.0)  # Close gripper
            time.sleep(1)
            
            print("  Lifting object...")
            self.controller.move_arm_absolute_pose(0, [0.30, 0.12, 0.20], [0, 0, 0])
            time.sleep(2)
            
            # Phase 2: Move to handoff position
            print("\n🤝 Phase 2: Moving to handoff position")
            print("  Both arms approaching handoff zone...")
            self.synchronized_movement([0.22, 0.05, 0.18], [0.22, -0.05, 0.18])
            time.sleep(2)
            
            # Phase 3: Handoff
            print("\n🔄 Phase 3: Object transfer")
            print("  Right arm positioning for receive...")
            self.controller.move_arm_absolute_pose(1, [0.20, -0.02, 0.18], [0, 0, -10])
            time.sleep(1)
            
            print("  Opening right gripper...")
            self.controller.control_gripper(1, 1.0)  # Open right gripper
            time.sleep(1)
            
            print("  Left arm placing object...")
            self.controller.move_arm_absolute_pose(0, [0.20, 0.02, 0.18], [0, 0, 10])
            time.sleep(1)
            
            print("  Right gripper closing (receiving object)...")
            self.controller.control_gripper(1, 0.0)  # Close right gripper
            time.sleep(1)
            
            print("  Left gripper opening (releasing object)...")
            self.controller.control_gripper(0, 1.0)  # Open left gripper
            time.sleep(1)
            
            # Phase 4: Separation
            print("\n↔️ Phase 4: Arms separating")
            print("  Right arm moving with object...")
            self.controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.22], [0, 0, 0])
            time.sleep(1)
            
            print("  Left arm returning to rest...")
            self.controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.22], [0, 0, 0])
            time.sleep(1)
            
            print("\n✅ Handoff simulation completed successfully!")
            print("🤖 Virtual object successfully transferred from left to right arm!")
            
            return True
            
        except Exception as e:
            print(f"❌ Handoff simulation failed: {e}")
            return False

    def run_all_demos(self):
        """Run all available demonstration patterns."""
        print("🎪 DUAL ARM ADVANCED DEMOS SUITE")
        print("="*70)
        
        demos = [
            ("Coordination Patterns", self.coordination_demo),
            ("Dance Choreography", self.dance_demo),
            ("Handoff Simulation", self.handoff_simulation)
        ]
        
        results = {}
        
        for demo_name, demo_func in demos:
            print(f"\n🎭 Starting {demo_name}...")
            success = demo_func()
            results[demo_name] = success
            
            if success:
                print(f"✅ {demo_name} completed successfully")
            else:
                print(f"❌ {demo_name} failed")
            
            time.sleep(2)  # Pause between demos
        
        # Final summary
        print("\n" + "="*70)
        print("🎊 DEMO SUITE SUMMARY")
        print("="*70)
        
        total_demos = len(results)
        successful_demos = sum(results.values())
        
        for demo_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"   {demo_name:<25}: {status}")
        
        print(f"\n🎯 Overall Result: {successful_demos}/{total_demos} demos successful")
        
        if successful_demos == total_demos:
            print("🎉 ALL DEMOS SUCCESSFUL! Dual robot coordination is excellent!")
        else:
            print("⚠️ Some demos had issues. Check individual outputs for details.")
        
        return successful_demos == total_demos


def main():
    """Main function with command line argument support."""
    # Initialize controller and coordinator
    try:
        controller = DualSO101Controller()
        coordinator = DualArmCoordinator(controller)
        
        # Initialize robot
        print("🔧 Initializing dual robot system...")
        result = controller.initialize_robot()
        if not result:
            print("❌ Robot initialization failed")
            print("💡 Make sure PhosphoBot server is running: phosphobot run")
            sys.exit(1)
        
        print("✅ Robot system initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize dual robot system: {e}")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        demo_arg = sys.argv[1].lower()
        
        if demo_arg == "--coordination":
            coordinator.coordination_demo()
        elif demo_arg == "--dance":
            coordinator.dance_demo()
        elif demo_arg == "--mirror":
            # Run just mirror movements
            print("🪞 Mirror Movement Demo")
            centers = [[0.25, 0.0, 0.20], [0.25, 0.0, 0.25], [0.30, 0.0, 0.22]]
            for center in centers:
                coordinator.mirror_movement(center)
                time.sleep(2)
        elif demo_arg == "--handoff":
            coordinator.handoff_simulation()
        else:
            print("❌ Unknown demo option. Available options:")
            print("   --coordination  : Coordination patterns demo")
            print("   --dance         : Dance choreography demo")
            print("   --mirror        : Mirror movements demo")
            print("   --handoff       : Handoff simulation demo")
            sys.exit(1)
    else:
        # Run all demos
        success = coordinator.run_all_demos()
        sys.exit(0 if success else 1)
    
    # Clean up
    try:
        controller.close()
        print("\n👋 Controller closed. Demo complete!")
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")


if __name__ == "__main__":
    main()
