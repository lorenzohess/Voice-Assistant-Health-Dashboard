# Health Dashboard Deployment Guide

## Quick Start (Raspberry Pi)

### 1. Clone and Setup

```bash
git clone <repo-url> ~/health-dashboard
cd ~/health-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Services

```bash
./scripts/install-services.sh
```

This installs:
- `health-dashboard` - **System service** (Flask web server on port 5000)
- `voice-assistant` - **User service** (needs PulseAudio for microphone access)

### 3. Start Services

```bash
# Web dashboard (system service)
sudo systemctl start health-dashboard

# Voice assistant (user service - no sudo)
systemctl --user start voice-assistant
```

Dashboard: `http://<pi-ip>:5000`

---

## Service Management

### Web Dashboard (System Service)

```bash
sudo systemctl start health-dashboard
sudo systemctl stop health-dashboard
sudo systemctl restart health-dashboard
sudo systemctl status health-dashboard

# View logs
journalctl -u health-dashboard -f
```

### Voice Assistant (User Service)

```bash
systemctl --user start voice-assistant
systemctl --user stop voice-assistant
systemctl --user restart voice-assistant
systemctl --user status voice-assistant

# View logs
journalctl --user -u voice-assistant -f
```

---

## Updating

After `git pull`:

```bash
./scripts/update.sh
```

---

## Voice Assistant Configuration

Edit `~/.config/systemd/user/voice-assistant.service`:

```ini
# Speech-to-text engine: vosk, whisper, or moonshine
Environment="STT_ENGINE=moonshine"

# Audio device (run: python -m voice.main --list-devices)
Environment="AUDIO_DEVICE=3"
```

After editing:
```bash
systemctl --user daemon-reload
systemctl --user restart voice-assistant
```

---

## Auto-Start on Boot

The web dashboard starts automatically on boot.

For voice assistant to start on boot (without login):
```bash
sudo loginctl enable-linger $USER
```

---

## Troubleshooting

### Voice assistant audio issues

```bash
# List audio devices
cd ~/health-dashboard && source venv/bin/activate
python -m voice.main --list-devices

# Test manually
python -m voice.main --debug
```

### Check service status

```bash
# Web dashboard
sudo systemctl status health-dashboard

# Voice assistant  
systemctl --user status voice-assistant
```

---

## Uninstalling

```bash
./scripts/uninstall-services.sh
```

---

## Files

| File | Description |
|------|-------------|
| `/etc/systemd/system/health-dashboard.service` | Web server (system) |
| `~/.config/systemd/user/voice-assistant.service` | Voice assistant (user) |
| `data/health.db` | Health data database |
| `data/foods.db` | Food database |
