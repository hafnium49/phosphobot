#!/bin/bash

# Script to run crane.py with alternative control and initialization
# This ensures the correct environment is activated and initializes the robot

echo "Activating phosphobot conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate phosphobot

echo "Starting crane robot control with ALTERNATIVE keyboard method AND INITIALIZATION..."
echo "This will initialize the robot first, then start alternative keyboard control"
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

# Change to the correct directory and run the script with alternative and init flags
cd /home/hafnium/aloha-lite/phosphobot/examples/02-control-with-keyboard
python crane.py --alternative --init
