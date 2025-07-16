#!/bin/bash

# Script to run crane.py with configurable robot ID
# Usage: ./run_crane_configurable.sh [ROBOT_ID]
# Default ROBOT_ID is 3 (left arm)

ROBOT_ID=${1:-3}  # Use first argument or default to 3

echo "Activating phosphobot conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate phosphobot

if [ "$ROBOT_ID" = "3" ]; then
    ARM_NAME="Left Arm"
elif [ "$ROBOT_ID" = "2" ]; then
    ARM_NAME="Right Arm"
else
    ARM_NAME="Arm $ROBOT_ID"
fi

echo "Starting crane robot control for $ARM_NAME (Robot ID $ROBOT_ID)..."
echo "Make sure this terminal window has focus for keyboard input!"
echo "Controls:"
echo "  Arrow keys: Move robot arm"
echo "  A/D: Move up/down"
echo "  Space: Toggle gripper"
echo "  J: Read current joint positions"
echo "  Ctrl+C: Exit"
echo ""
echo "Note: Robot initialization is skipped by default"
echo "Use 'python crane.py --robot-id $ROBOT_ID --init' if you need to initialize the robot first"
echo ""

# Change to the correct directory and run the script
cd /home/hafnium/aloha-lite/phosphobot/examples/02-control-with-keyboard
python crane.py --robot-id "$ROBOT_ID"
