#!/bin/bash
# Setup script for phosphobot conda environment

set -e  # Exit on error

echo "Setting up phosphobot conda environment..."

# Check if Miniconda is installed
if [ ! -d "$HOME/miniconda3" ]; then
    echo "Miniconda not found. Installing Miniconda..."

    # Download Miniconda installer
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda_installer.sh

    # Install Miniconda silently
    bash ~/miniconda_installer.sh -b -p $HOME/miniconda3

    # Clean up installer
    rm ~/miniconda_installer.sh

    # Initialize conda
    $HOME/miniconda3/bin/conda init bash

    echo "Miniconda installed. Please restart your terminal or run: source ~/.bashrc"
fi

# Activate conda
source $HOME/miniconda3/bin/activate

# Accept Terms of Service if needed
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>/dev/null || true
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r 2>/dev/null || true

# Check if environment exists
if conda env list | grep -q "^phosphobot "; then
    echo "Environment 'phosphobot' already exists. Activating it..."
    conda activate phosphobot
else
    echo "Creating conda environment 'phosphobot' with Python 3.10..."
    conda create -n phosphobot python=3.10 -y
    conda activate phosphobot

    echo "Installing phosphobot package..."
    pip install phosphobot
fi

echo ""
echo "Setup complete! To use the phosphobot environment, run:"
echo "  conda activate phosphobot"
echo ""
echo "To verify the installation, run:"
echo "  python -c 'import phosphobot; print(phosphobot.__version__)'"