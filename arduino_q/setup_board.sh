#!/bin/bash
# setup_board.sh - Sets up dependencies and venv on Arduino Q (Debian 13 aarch64)

# Exit on any error
set -e

echo "=== System Package Installation ==="
echo "Updating apt packages..."
sudo apt-get update

echo "Installing required system packages (build-essential, python3-dev, OpenCV/PyTorch requirements)..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1

echo "=== Python Virtual Environment Setup ==="
if [ ! -d "venv" ]; then
    echo "Creating virtual environment 'venv'..."
    python3 -m venv venv
else
    echo "Virtual environment 'venv' already exists."
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing CPU-only PyTorch and torchvision..."
pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo "Installing remaining Python packages from requirements.txt..."
# Check path of requirements.txt relative to the execution context
if [ -f "requirements.txt" ]; then
    pip install --no-cache-dir -r requirements.txt
elif [ -f "../requirements.txt" ]; then
    pip install --no-cache-dir -r ../requirements.txt
else
    echo "Error: requirements.txt not found!"
    exit 1
fi

echo "=== Setup Completed Successfully ==="
echo "To run the tracking app in headless mode:"
echo "  source venv/bin/activate"
echo "  python main_tracking.py --camera /dev/video0 --headless"
