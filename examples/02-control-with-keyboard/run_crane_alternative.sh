#!/bin/bash

# Script to run crane.py with alternative keyboard control (option 2)
# This ensures the correct environment is activated and forces alternative control

echo "Activating phosphobot conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate phosphobot

echo "Starting crane robot control with ALTERNATIVE keyboard method..."
echo "Make sure this terminal window has focus for keyboard input!"
echo "Alternative Controls:"
echo "  W: Move forward"
echo "  S: Move backward"
echo "  A: Move up"
echo "  D: Move down"
echo "  J: Read joint positions"
echo "  Space: Toggle gripper"
echo "  Q: Quit"
echo ""
echo "Note: Robot initialization is skipped by default"
echo "Add '--init' flag if you need to initialize the robot first"
echo ""

# Change to the correct directory and run the script with alternative flag
cd /home/hafnium/aloha-lite/phosphobot/examples/02-control-with-keyboard
python crane.py --alternative
