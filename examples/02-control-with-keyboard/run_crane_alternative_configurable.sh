#!/bin/bash

# Script to run crane.py with alternative control and configurable robot ID
# Usage: ./run_crane_alternative_configurable.sh [ROBOT_ID]
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

echo "Starting crane robot control for $ARM_NAME (Robot ID $ROBOT_ID) with ALTERNATIVE keyboard method..."
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

# Change to the correct directory and run the script with alternative and robot-id flags
cd /home/hafnium/aloha-lite/phosphobot/examples/02-control-with-keyboard
python crane.py --alternative --robot-id "$ROBOT_ID"
