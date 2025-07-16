#!/bin/bash

# Script to run crane.py with initialization and standard keyboard control
# This ensures the correct environment is activated and initializes the robot

echo "Activating phosphobot conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate phosphobot

echo "Starting crane robot control WITH INITIALIZATION..."
echo "This will initialize the robot first, then start keyboard control"
echo "Make sure this terminal window has focus for keyboard input!"
echo "Controls:"
echo "  Arrow keys: Move robot arm"
echo "  A/D: Move up/down"
echo "  Space: Toggle gripper"
echo "  J: Read current joint positions"
echo "  Ctrl+C: Exit"
echo ""

# Change to the correct directory and run the script with init flag
cd /home/hafnium/aloha-lite/phosphobot/examples/02-control-with-keyboard
python crane.py --init
