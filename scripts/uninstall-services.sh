#!/bin/bash
# Uninstall systemd services for Health Dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Health Dashboard Service Uninstallation ==="
echo ""

# Detect the user who owns the project
PROJECT_USER=$(stat -c '%U' "$PROJECT_DIR")
PROJECT_HOME=$(eval echo ~$PROJECT_USER)

# --- Uninstall voice-assistant USER service ---
echo "=== Removing voice-assistant (user service) ==="

USER_SERVICE_FILE="$PROJECT_HOME/.config/systemd/user/voice-assistant.service"

if [ "$USER" = "$PROJECT_USER" ]; then
    systemctl --user stop voice-assistant.service 2>/dev/null || true
    systemctl --user disable voice-assistant.service 2>/dev/null || true
fi

rm -f "$USER_SERVICE_FILE"
echo "  Removed: $USER_SERVICE_FILE"

# --- Uninstall alarm USER service ---
echo ""
echo "=== Removing alarm (user service) ==="

ALARM_SERVICE_FILE="$PROJECT_HOME/.config/systemd/user/alarm.service"

if [ "$USER" = "$PROJECT_USER" ]; then
    systemctl --user stop alarm.service 2>/dev/null || true
    systemctl --user disable alarm.service 2>/dev/null || true
fi

rm -f "$ALARM_SERVICE_FILE"
echo "  Removed: $ALARM_SERVICE_FILE"

if [ "$USER" = "$PROJECT_USER" ]; then
    systemctl --user daemon-reload
fi

# --- Uninstall health-dashboard SYSTEM service ---
echo ""
echo "=== Removing health-dashboard (system service) ==="

if [ "$EUID" -ne 0 ]; then
    echo "Removing system service requires sudo..."
    sudo systemctl stop health-dashboard.service 2>/dev/null || true
    sudo systemctl disable health-dashboard.service 2>/dev/null || true
    sudo rm -f /etc/systemd/system/health-dashboard.service
    sudo systemctl daemon-reload
else
    systemctl stop health-dashboard.service 2>/dev/null || true
    systemctl disable health-dashboard.service 2>/dev/null || true
    rm -f /etc/systemd/system/health-dashboard.service
    systemctl daemon-reload
fi

echo "  Removed: /etc/systemd/system/health-dashboard.service"

echo ""
echo "=== Uninstallation Complete ==="
