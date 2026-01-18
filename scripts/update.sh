#!/bin/bash
# Update script for Health Dashboard on Raspberry Pi
# Run this after git pull - preserves existing data, updates code and restarts services

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Health Dashboard Update Script ==="
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

# Update database schema (add new tables/columns without deleting data)
echo "Updating database schema..."
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Database schema updated')"

# Run migrations for existing columns
echo "Running migrations..."
python scripts/migrate_db.py

# Check if systemd services are installed
USE_SYSTEMD=false
if systemctl list-unit-files health-dashboard.service &>/dev/null; then
    USE_SYSTEMD=true
fi

if [ "$USE_SYSTEMD" = true ]; then
    echo ""
    echo "Using systemd to manage services..."
    
    # Restart services
    echo "Restarting health-dashboard service..."
    sudo systemctl restart health-dashboard.service || true
    
    if systemctl list-unit-files voice-assistant.service &>/dev/null; then
        echo "Restarting voice-assistant service..."
        sudo systemctl restart voice-assistant.service || true
    fi
    
    sleep 2
    
    # Check status
    echo ""
    echo "=== Service Status ==="
    systemctl status health-dashboard.service --no-pager -l || true
    
    echo ""
    echo "=== Update Complete ==="
    echo "Dashboard running at: http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo "View logs:"
    echo "  journalctl -u health-dashboard -f"
    echo "  journalctl -u voice-assistant -f"
else
    echo ""
    echo "Systemd services not installed. Using legacy mode..."
    
    # Stop any existing Flask server
    echo "Stopping existing server..."
    pkill -f "python run.py" 2>/dev/null || true
    pkill -f "voice.main" 2>/dev/null || true
    sleep 1

    # Start the server
    echo "Starting Flask server..."
    nohup python run.py > /tmp/health-dashboard.log 2>&1 &
    sleep 2

    # Check if server started
    if pgrep -f "python run.py" > /dev/null; then
        echo ""
        echo "=== Update Complete ==="
        echo "Dashboard running at: http://$(hostname -I | awk '{print $1}'):5000"
        echo "Logs at: /tmp/health-dashboard.log"
        echo ""
        echo "To install systemd services for better management:"
        echo "  sudo ./scripts/install-services.sh"
    else
        echo "ERROR: Server failed to start. Check /tmp/health-dashboard.log"
        exit 1
    fi
fi
