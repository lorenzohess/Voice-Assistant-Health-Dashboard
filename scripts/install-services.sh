#!/bin/bash
# Install systemd services for Health Dashboard
# - health-dashboard: system service (runs web server)
# - voice-assistant: user service (needs PulseAudio access)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Health Dashboard Service Installation ==="
echo "Project directory: $PROJECT_DIR"
echo ""

# Detect the user who owns the project
PROJECT_USER=$(stat -c '%U' "$PROJECT_DIR")
PROJECT_GROUP=$(stat -c '%G' "$PROJECT_DIR")
PROJECT_HOME=$(eval echo ~$PROJECT_USER)
echo "Detected user: $PROJECT_USER"
echo "Detected home: $PROJECT_HOME"
echo ""

# --- Install health-dashboard as SYSTEM service (needs sudo) ---
echo "=== Installing health-dashboard (system service) ==="

if [ "$EUID" -ne 0 ]; then
    echo "Installing system service requires sudo..."
    sudo sed -e "s|User=pi2|User=$PROJECT_USER|g" \
        -e "s|Group=pi2|Group=$PROJECT_GROUP|g" \
        -e "s|/home/pi2/health-dashboard|$PROJECT_DIR|g" \
        "$SCRIPT_DIR/health-dashboard.service" > /tmp/health-dashboard.service
    sudo mv /tmp/health-dashboard.service /etc/systemd/system/health-dashboard.service
    sudo systemctl daemon-reload
    sudo systemctl enable health-dashboard.service
else
    sed -e "s|User=pi2|User=$PROJECT_USER|g" \
        -e "s|Group=pi2|Group=$PROJECT_GROUP|g" \
        -e "s|/home/pi2/health-dashboard|$PROJECT_DIR|g" \
        "$SCRIPT_DIR/health-dashboard.service" > /etc/systemd/system/health-dashboard.service
    systemctl daemon-reload
    systemctl enable health-dashboard.service
fi

echo "  Installed: /etc/systemd/system/health-dashboard.service"

# --- Install voice-assistant as USER service (no sudo needed) ---
echo ""
echo "=== Installing voice-assistant (user service) ==="

USER_SERVICE_DIR="$PROJECT_HOME/.config/systemd/user"
mkdir -p "$USER_SERVICE_DIR"

# Create service file with correct paths (symlink won't work with sed substitution)
sed -e "s|/home/pi2/health-dashboard|$PROJECT_DIR|g" \
    "$SCRIPT_DIR/voice-assistant.service" > "$USER_SERVICE_DIR/voice-assistant.service"

echo "  Installed: $USER_SERVICE_DIR/voice-assistant.service"

# --- Install alarm as USER service (needs PulseAudio for mpv) ---
echo ""
echo "=== Installing alarm (user service) ==="

sed -e "s|/home/pi2/health-dashboard|$PROJECT_DIR|g" \
    "$SCRIPT_DIR/alarm.service" > "$USER_SERVICE_DIR/alarm.service"

echo "  Installed: $USER_SERVICE_DIR/alarm.service"

# Reload user daemon (must run as the target user)
if [ "$USER" = "$PROJECT_USER" ]; then
    systemctl --user daemon-reload
    systemctl --user enable voice-assistant.service
    systemctl --user enable alarm.service
    echo "  Enabled voice-assistant user service"
    echo "  Enabled alarm user service"
else
    echo "  NOTE: Run as $PROJECT_USER to enable:"
    echo "    systemctl --user daemon-reload"
    echo "    systemctl --user enable voice-assistant"
    echo "    systemctl --user enable alarm"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "System service (web dashboard):"
echo "  sudo systemctl start health-dashboard"
echo "  sudo systemctl status health-dashboard"
echo "  journalctl -u health-dashboard -f"
echo ""
echo "User services (run as $PROJECT_USER):"
echo ""
echo "  Voice assistant:"
echo "    systemctl --user start voice-assistant"
echo "    systemctl --user status voice-assistant"
echo "    journalctl --user -u voice-assistant -f"
echo ""
echo "  Alarm:"
echo "    systemctl --user start alarm"
echo "    systemctl --user status alarm"
echo "    journalctl --user -u alarm -f"
echo ""
echo "To start all services:"
echo "  sudo systemctl start health-dashboard"
echo "  systemctl --user start voice-assistant"
echo "  systemctl --user start alarm"