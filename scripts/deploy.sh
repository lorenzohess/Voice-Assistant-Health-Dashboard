#!/bin/bash
# Deploy script for Health Dashboard on Raspberry Pi
# Run this after git pull to update dependencies and restart the server

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Health Dashboard Deploy Script ==="
echo "Project directory: $PROJECT_DIR"

cd "$PROJECT_DIR"

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Recreate database with new schema
echo "Recreating database..."
rm -f data/health.db
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Database schema created')"

# Add sample data (includes Vegetable Servings)
echo "Adding sample data..."
python scripts/add_sample_data.py

# Stop any existing Flask server
echo "Stopping existing server..."
pkill -f "python run.py" 2>/dev/null || true
sleep 1

# Start the server
echo "Starting Flask server..."
nohup python run.py > /tmp/health-dashboard.log 2>&1 &
sleep 2

# Check if server started
if pgrep -f "python run.py" > /dev/null; then
    echo ""
    echo "=== Deploy Complete ==="
    echo "Dashboard running at: http://$(hostname -I | awk '{print $1}'):5000"
    echo "Logs at: /tmp/health-dashboard.log"
else
    echo "ERROR: Server failed to start. Check /tmp/health-dashboard.log"
    exit 1
fi
