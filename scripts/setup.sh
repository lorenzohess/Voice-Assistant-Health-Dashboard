#!/bin/bash
# Setup script for Health Dashboard
# Works on both Arch Linux and Raspberry Pi OS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Setting up Health Dashboard..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directory
mkdir -p data

echo ""
echo "Setup complete!"
echo ""
echo "To run the dashboard:"
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  python run.py"
echo ""
echo "To add sample data for testing:"
echo "  python scripts/add_sample_data.py"
echo ""
echo "Dashboard will be available at http://localhost:5000"
