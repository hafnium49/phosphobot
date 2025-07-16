#!/bin/bash

# Script to run crane.py with the phosphobot conda environment
# This ensures the correct environment is activated and dependencies are available

echo "Activating phosphobot conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate phosphobot

echo "Starting crane robot control..."
echo "Make sure this terminal window has focus for keyboard input!"
echo "Controls:"
echo "  Arrow keys: Move robot arm"
echo "  A/D: Move up/down"
echo "  Space: Toggle gripper"
echo "  J: Read current joint positions"
echo "  Ctrl+C: Exit"
echo ""
echo "Note: Robot initialization is skipped by default"
echo "Use 'python crane.py --init' if you need to initialize the robot first"
echo ""

# Change to the correct directory and run the script
cd /home/hafnium/aloha-lite/phosphobot/examples/02-control-with-keyboard
python crane.py
