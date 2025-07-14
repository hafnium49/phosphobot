#!/usr/bin/env python3
"""
Interactive SO-101 Control (Single Robot Version)

This script provides an interactive command-line interface for controlling
a single SO-101 robotic arm with real-time pose adjustments.

CORRECTED VERSION: Adapted from interactive_control.py to work with single robot setup.
"""

import sys
import time
from dual_so101_controller import DualSO101Controller


class InteractiveControllerSingle:
    """Interactive command-line controller for single SO-101 arm."""
    
    def __init__(self):
        self.controller = DualSO101Controller()
        self.robot_id = 0  # Always use robot 0 for single robot setup
        self.step_size = 0.02  # 2cm default step size
        
        # Initialize robot
        print("🔧 Initializing robot...")
        result = self.controller.initialize_robot()
        if result:
            print(f"✅ Robot initialized: {result}")
        else:
            print("❌ Robot initialization failed")
            sys.exit(1)
    
    def print_menu(self):
        """Print the interactive control menu."""
        print(f"\n🤖 Interactive SO-101 Control (Single Robot)")
        print(f"============================================")
        print(f"Robot ID: {self.robot_id}")
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
        print("  +/- - Increase/decrease step size")
        print("  p   - Print current pose (disabled - /pose endpoint unavailable)")
        print("  z   - Go to safe position")
        print("  m   - Show this menu")
        print("  x   - Exit")
        print()
        print("💡 Related Examples:")
        print("  - single_arm_basic.py: Basic single-arm control")
        print("  - single_arm_test_clean.py: Test movements")
        print("  - dual_so101_controller.py: Controller library")
        print()
    
    def get_current_pose_info(self):
        """Get and display current pose information."""
        print(f"\n⚠️ Current pose info disabled - /pose endpoint not available")
        print(f"💡 The robot remembers its position internally")
        return None
    
    def safe_position(self):
        """Move arm to a safe position."""
        try:
            safe_pos = [0.25, 0.0, 0.20]  # Centered safe position
            self.controller.move_arm_absolute_pose(
                robot_id=self.robot_id,
                position=safe_pos,
                orientation=[0, 0, 0]
            )
            print(f"✅ Robot moved to safe position: {safe_pos}")
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
        
        if command in movement_map:
            delta_pos = movement_map[command]
            try:
                self.controller.move_arm_relative_pose(
                    robot_id=self.robot_id,
                    delta_position=delta_pos
                )
                direction = {
                    'w': 'forward', 's': 'backward', 'a': 'left',
                    'd': 'right', 'q': 'up', 'e': 'down'
                }[command]
                print(f"✅ Moved {direction} by {step_cm:.1f}cm")
            except Exception as e:
                print(f"❌ Movement failed: {e}")
        
        # Handle rotations (Note: These may not work as expected without pose feedback)
        rotation_map = {
            'r': [0, 5, 0],    # Pitch up
            'f': [0, -5, 0],   # Pitch down
            't': [0, 0, 5],    # Yaw left  
            'g': [0, 0, -5],   # Yaw right
            'y': [5, 0, 0],    # Roll left
            'h': [-5, 0, 0],   # Roll right
        }
        
        if command in rotation_map:
            print(f"⚠️ Rotation commands disabled - require pose feedback not available")
            print(f"💡 Use absolute positioning with orientation instead")
    
    def handle_gripper(self, command: str):
        """Handle gripper commands."""
        if command == 'o':
            try:
                self.controller.control_gripper(self.robot_id, 1.0)
                print("✅ Gripper opened")
            except Exception as e:
                print(f"❌ Failed to open gripper: {e}")
        elif command == 'c':
            try:
                self.controller.control_gripper(self.robot_id, 0.0)
                print("✅ Gripper closed")
            except Exception as e:
                print(f"❌ Failed to close gripper: {e}")
    
    def handle_control(self, command: str):
        """Handle control commands."""
        if command == '+':
            self.step_size = min(0.10, self.step_size + 0.01)  # Max 10cm
            print(f"✅ Step size increased to {self.step_size * 100:.1f}cm")
        elif command == '-':
            self.step_size = max(0.005, self.step_size - 0.01)  # Min 0.5cm
            print(f"✅ Step size decreased to {self.step_size * 100:.1f}cm")
        elif command == 'p':
            self.get_current_pose_info()
        elif command == 'z':
            self.safe_position()
        elif command == 'm':
            self.print_menu()
    
    def run(self):
        """Run the interactive control loop."""
        print("🚀 Starting interactive control...")
        self.safe_position()  # Start in safe position
        time.sleep(1)
        self.print_menu()
        
        try:
            while True:
                command = input("\n> ").strip().lower()
                
                if command == 'x':
                    break
                elif command in 'wsadqe':
                    self.handle_movement(command)
                elif command in 'rftygh':
                    self.handle_movement(command)
                elif command in 'oc':
                    self.handle_gripper(command)
                elif command in '+-pzm':
                    self.handle_control(command)
                else:
                    print("❓ Unknown command. Type 'm' for menu or 'x' to exit.")
        
        except KeyboardInterrupt:
            print("\n\n⌨️ Ctrl+C pressed")
        except EOFError:
            print("\n\n📜 EOF reached")
        
        finally:
            self.controller.close()
            print("👋 Interactive control ended. Goodbye!")


def main():
    """Main function."""
    try:
        controller = InteractiveControllerSingle()
        controller.run()
    except Exception as e:
        print(f"❌ Failed to start interactive control: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
