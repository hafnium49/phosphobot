#!/usr/bin/env python3
"""
Interactive Dual SO-101 Control

This script provides an interactive command-line interface for controlling
dual SO-101 robotic arms with real-time pose adjustments.
"""

import sys
import time
from dual_so101_controller import DualSO101Controller


class InteractiveController:
    """Interactive command-line controller for dual SO-101 arms."""
    
    def __init__(self):
        self.controller = DualSO101Controller()
        self.active_arm = 0  # 0 for left, 1 for right
        self.step_size = 0.02  # 2cm default step size
    
    def print_menu(self):
        """Print the interactive control menu."""
        arm_name = "Left" if self.active_arm == 0 else "Right"
        print(f"\n🤖 Interactive Dual SO-101 Control")
        print(f"================================")
        print(f"Active Arm: {arm_name} (ID: {self.active_arm})")
        print(f"Step Size: {self.step_size * 100:.1f}cm")
        print()
        print("Movement Commands:")
        print("  w/s - Move forward/backward")
        print("  a/d - Move left/right") 
        print("  q/e - Move up/down")
        print("  r/f - Rotate pitch up/down")
        print("  t/g - Rotate yaw left/right")
        print("  y/h - Rotate roll left/right")
        print()
        print("Gripper Commands:")
        print("  o   - Open gripper")
        print("  c   - Close gripper")
        print()
        print("Control Commands:")
        print("  0/1 - Switch to arm 0/1")
        print("  +/- - Increase/decrease step size")
        print("  p   - Print current pose")
        print("  z   - Go to safe position")
        print("  m   - Show this menu")
        print("  x   - Exit")
        print()
    
    def get_current_pose_info(self, robot_id: int):
        """Get and display current pose information."""
        try:
            pose = self.controller.get_current_pose(robot_id)
            arm_name = "Left" if robot_id == 0 else "Right"
            print(f"\n📍 {arm_name} Arm Current Pose:")
            print(f"   Position: {pose}")
            return pose
        except Exception as e:
            print(f"❌ Failed to get pose for arm {robot_id}: {e}")
            return None
    
    def safe_position(self, robot_id: int):
        """Move arm to a safe position."""
        try:
            safe_pos = [0.25, 0.15 if robot_id == 0 else -0.15, 0.20]
            self.controller.move_arm_absolute_pose(
                robot_id=robot_id,
                position=safe_pos,
                orientation=[0, 0, 0]
            )
            arm_name = "Left" if robot_id == 0 else "Right"
            print(f"✅ {arm_name} arm moved to safe position")
        except Exception as e:
            print(f"❌ Failed to move to safe position: {e}")
    
    def handle_movement(self, command: str):
        """Handle movement commands."""
        step_cm = self.step_size * 100  # Convert to cm for relative movements
        
        movement_map = {
            'w': [step_cm, 0, 0],      # Forward
            's': [-step_cm, 0, 0],     # Backward
            'a': [0, step_cm, 0],      # Left
            'd': [0, -step_cm, 0],     # Right
            'q': [0, 0, step_cm],      # Up
            'e': [0, 0, -step_cm],     # Down
        }
        
        rotation_map = {
            'r': [0, 0, 0, 5, 0, 0],   # Pitch up
            'f': [0, 0, 0, -5, 0, 0],  # Pitch down
            't': [0, 0, 0, 0, 5, 0],   # Yaw left
            'g': [0, 0, 0, 0, -5, 0],  # Yaw right
            'y': [0, 0, 0, 0, 0, 5],   # Roll left
            'h': [0, 0, 0, 0, 0, -5],  # Roll right
        }
        
        try:
            if command in movement_map:
                delta_pos = movement_map[command]
                self.controller.move_arm_relative_pose(
                    robot_id=self.active_arm,
                    delta_position=delta_pos
                )
                arm_name = "Left" if self.active_arm == 0 else "Right"
                print(f"✅ {arm_name} arm moved: {delta_pos}")
                
            elif command in rotation_map:
                delta_rot = rotation_map[command][3:6]  # Extract rotation part
                self.controller.move_arm_relative_pose(
                    robot_id=self.active_arm,
                    delta_position=[0, 0, 0],
                    delta_orientation=delta_rot
                )
                arm_name = "Left" if self.active_arm == 0 else "Right"
                print(f"✅ {arm_name} arm rotated: {delta_rot}")
                
        except Exception as e:
            print(f"❌ Movement failed: {e}")
    
    def run(self):
        """Run the interactive control loop."""
        print("🚀 Starting Interactive Dual SO-101 Control")
        print("Make sure both arms are connected and phosphobot server is running!")
        
        # Initial setup
        try:
            # Move both arms to safe starting positions
            print("\n🔧 Moving arms to safe starting positions...")
            self.safe_position(0)
            self.safe_position(1)
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Warning: Could not move to safe positions: {e}")
        
        self.print_menu()
        
        print("Ready for commands! Type 'm' for menu, 'x' to exit.")
        
        while True:
            try:
                # Get user input
                command = input(f"\n[Arm {self.active_arm}]> ").strip().lower()
                
                if not command:
                    continue
                
                # Handle commands
                if command == 'x':
                    print("👋 Exiting interactive control...")
                    break
                
                elif command == 'm':
                    self.print_menu()
                
                elif command == '0':
                    self.active_arm = 0
                    print("✅ Switched to Left arm (ID: 0)")
                
                elif command == '1':
                    self.active_arm = 1
                    print("✅ Switched to Right arm (ID: 1)")
                
                elif command == '+':
                    self.step_size = min(0.05, self.step_size + 0.005)
                    print(f"✅ Step size increased to {self.step_size * 100:.1f}cm")
                
                elif command == '-':
                    self.step_size = max(0.005, self.step_size - 0.005)
                    print(f"✅ Step size decreased to {self.step_size * 100:.1f}cm")
                
                elif command == 'o':
                    self.controller.control_gripper(self.active_arm, 1.0)
                
                elif command == 'c':
                    self.controller.control_gripper(self.active_arm, 0.0)
                
                elif command == 'p':
                    self.get_current_pose_info(self.active_arm)
                
                elif command == 'z':
                    self.safe_position(self.active_arm)
                
                elif command in 'wsadqerftgyh':
                    self.handle_movement(command)
                
                else:
                    print(f"❓ Unknown command: '{command}'. Type 'm' for menu.")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Cleanup
        try:
            self.controller.close()
            print("✅ Controller closed successfully")
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")


def main():
    """Main function."""
    try:
        interactive = InteractiveController()
        interactive.run()
    except Exception as e:
        print(f"❌ Failed to start interactive controller: {e}")
        print("💡 Make sure phosphobot server is running: phosphobot run")
        sys.exit(1)


if __name__ == "__main__":
    main()
