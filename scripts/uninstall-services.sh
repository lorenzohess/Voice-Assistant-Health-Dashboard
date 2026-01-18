#!/bin/bash
# Uninstall systemd services for Health Dashboard
# Run as: sudo ./scripts/uninstall-services.sh

set -e

echo "=== Health Dashboard Service Uninstallation ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Stop services
echo "Stopping services..."
systemctl stop health-dashboard.service 2>/dev/null || true
systemctl stop voice-assistant.service 2>/dev/null || true

# Disable services
echo "Disabling services..."
systemctl disable health-dashboard.service 2>/dev/null || true
systemctl disable voice-assistant.service 2>/dev/null || true

# Remove service files
echo "Removing service files..."
rm -f /etc/systemd/system/health-dashboard.service
rm -f /etc/systemd/system/voice-assistant.service

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

echo ""
echo "=== Uninstallation Complete ==="
