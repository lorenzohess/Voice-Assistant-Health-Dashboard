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

### 2. Install Systemd Services

```bash
sudo ./scripts/install-services.sh
```

This installs two services:
- `health-dashboard` - Flask web server on port 5000
- `voice-assistant` - Voice control with wake word "Hey Jarvis"

### 3. Start Services

```bash
sudo systemctl start health-dashboard voice-assistant
```

Dashboard will be available at `http://<pi-ip>:5000`

---

## Service Management

### Start/Stop

```bash
# Start
sudo systemctl start health-dashboard
sudo systemctl start voice-assistant

# Stop
sudo systemctl stop health-dashboard
sudo systemctl stop voice-assistant

# Restart
sudo systemctl restart health-dashboard voice-assistant
```

### View Logs

```bash
# Dashboard logs
journalctl -u health-dashboard -f

# Voice assistant logs
journalctl -u voice-assistant -f

# Both (last 100 lines)
journalctl -u health-dashboard -u voice-assistant -n 100
```

### Check Status

```bash
sudo systemctl status health-dashboard voice-assistant
```

---

## Updating

After `git pull`:

```bash
./scripts/update.sh
```

This will:
1. Update Python dependencies
2. Run database migrations
3. Restart services (if using systemd)

---

## Voice Assistant Configuration

Edit environment variables in `/etc/systemd/system/voice-assistant.service`:

```ini
# Speech-to-text engine: vosk, whisper, or moonshine
Environment=STT_ENGINE=moonshine

# API URL for the Flask dashboard
Environment=HEALTH_API_URL=http://localhost:5000

# Disable Hugging Face online checks (after first run)
Environment=HF_HUB_OFFLINE=1
```

After editing:
```bash
sudo systemctl daemon-reload
sudo systemctl restart voice-assistant
```

---

## Troubleshooting

### Dashboard won't start

```bash
# Check logs
journalctl -u health-dashboard -n 50

# Test manually
cd ~/health-dashboard
source venv/bin/activate
python run.py
```

### Voice assistant won't start

```bash
# Check audio devices
arecord -l
aplay -l

# Check user is in audio group
groups

# Test manually
cd ~/health-dashboard
source venv/bin/activate
python -m voice.main --debug
```

### No wake word detection

```bash
# Test microphone
python -m voice.listener --test-mic

# Test wake word
python -m voice.listener --test-wake
```

---

## Uninstalling

```bash
sudo ./scripts/uninstall-services.sh
```

---

## Files

| File | Description |
|------|-------------|
| `scripts/install-services.sh` | Install systemd services |
| `scripts/uninstall-services.sh` | Remove systemd services |
| `scripts/update.sh` | Update code and restart services |
| `scripts/health-dashboard.service` | Systemd service template (web) |
| `scripts/voice-assistant.service` | Systemd service template (voice) |
| `data/health.db` | SQLite database (health data) |
| `data/foods.db` | SQLite database (food database) |
