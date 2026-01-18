"""Alarm module for scheduled music playback."""

from pathlib import Path

# Base paths
ALARM_DIR = Path(__file__).parent
PROJECT_DIR = ALARM_DIR.parent
MUSIC_DIR = PROJECT_DIR / "music"
CONFIG_FILE = PROJECT_DIR / "data" / "alarm_config.json"
