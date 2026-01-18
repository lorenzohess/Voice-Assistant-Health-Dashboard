#!/bin/bash
# Install systemd services for Health Dashboard
# Run as: sudo ./scripts/install-services.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Health Dashboard Service Installation ==="
echo "Project directory: $PROJECT_DIR"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Detect the user who owns the project
PROJECT_USER=$(stat -c '%U' "$PROJECT_DIR")
PROJECT_GROUP=$(stat -c '%G' "$PROJECT_DIR")
echo "Detected user: $PROJECT_USER"
echo "Detected group: $PROJECT_GROUP"
echo ""

# Update service files with correct paths and user
echo "Installing health-dashboard.service..."
sed -e "s|User=pi2|User=$PROJECT_USER|g" \
    -e "s|Group=pi2|Group=$PROJECT_GROUP|g" \
    -e "s|/home/pi2/health-dashboard|$PROJECT_DIR|g" \
    "$SCRIPT_DIR/health-dashboard.service" > /etc/systemd/system/health-dashboard.service

echo "Installing voice-assistant.service..."
sed -e "s|User=pi2|User=$PROJECT_USER|g" \
    -e "s|Group=pi2|Group=$PROJECT_GROUP|g" \
    -e "s|/home/pi2/health-dashboard|$PROJECT_DIR|g" \
    "$SCRIPT_DIR/voice-assistant.service" > /etc/systemd/system/voice-assistant.service

# Reload systemd
echo ""
echo "Reloading systemd..."
systemctl daemon-reload

# Enable services
echo "Enabling services..."
systemctl enable health-dashboard.service
systemctl enable voice-assistant.service

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Commands:"
echo "  Start dashboard:    sudo systemctl start health-dashboard"
echo "  Start voice:        sudo systemctl start voice-assistant"
echo "  Start both:         sudo systemctl start health-dashboard voice-assistant"
echo ""
echo "  Stop dashboard:     sudo systemctl stop health-dashboard"
echo "  Stop voice:         sudo systemctl stop voice-assistant"
echo ""
echo "  View logs:          journalctl -u health-dashboard -f"
echo "  View voice logs:    journalctl -u voice-assistant -f"
echo ""
echo "  Status:             sudo systemctl status health-dashboard voice-assistant"
echo ""
echo "To start services now:"
echo "  sudo systemctl start health-dashboard voice-assistant"
