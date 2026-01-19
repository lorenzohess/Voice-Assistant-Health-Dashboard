"""Scheduler for alarm using APScheduler."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import CONFIG_FILE, PROJECT_DIR
from .player import play_random_playlist, stop_playback
from .display import display_on

# Config files
DISPLAY_CONFIG_FILE = PROJECT_DIR / "data" / "display_config.json"

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None

# Job IDs
ALARM_JOB_ID = "morning_alarm"
DISPLAY_WAKE_JOB_ID = "display_wake"
CONFIG_CHECK_JOB_ID = "config_check"

# Track config file modification times
_last_config_mtime: float = 0
_last_display_config_mtime: float = 0


def load_config() -> dict:
    """Load alarm configuration from JSON file."""
    default_config = {
        "enabled": True,
        "time": "08:00",
        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }
    
    if not CONFIG_FILE.exists():
        return default_config
    
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        # Merge with defaults for any missing keys
        return {**default_config, **config}
    except (json.JSONDecodeError, IOError) as e:
        print(f"[Alarm] Error loading config: {e}")
        return default_config


def save_config(config: dict) -> bool:
    """Save alarm configuration to JSON file."""
    try:
        # Ensure data directory exists
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
        return True
    except IOError as e:
        print(f"[Alarm] Error saving config: {e}")
        return False


def load_display_config() -> dict:
    """Load display configuration from JSON file."""
    default_config = {
        "wake_time": "07:00",
        "wake_enabled": True
    }
    
    if not DISPLAY_CONFIG_FILE.exists():
        return default_config
    
    try:
        with open(DISPLAY_CONFIG_FILE, "r") as f:
            config = json.load(f)
        return {**default_config, **config}
    except (json.JSONDecodeError, IOError) as e:
        print(f"[Display] Error loading config: {e}")
        return default_config


def _alarm_trigger():
    """Called when alarm triggers."""
    print(f"[Alarm] Alarm triggered at {datetime.now().strftime('%H:%M')}")
    play_random_playlist()


def _display_wake_trigger():
    """Called when display wake time is reached."""
    print(f"[Display] Wake triggered at {datetime.now().strftime('%H:%M')}")
    display_on()


def get_scheduler() -> BackgroundScheduler:
    """Get or create the scheduler instance."""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    
    return _scheduler


def reload_schedule() -> bool:
    """Reload the alarm schedule from config."""
    scheduler = get_scheduler()
    config = load_config()
    
    # Remove existing alarm job if present
    try:
        scheduler.remove_job(ALARM_JOB_ID)
    except Exception:
        pass  # Job might not exist
    
    if not config.get("enabled", True):
        print("[Alarm] Alarm is disabled")
    else:
        # Parse time
        time_str = config.get("time", "08:00")
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            print(f"[Alarm] Invalid time format: {time_str}")
            return False
        
        # Parse days
        days = config.get("days", ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
        day_of_week = ",".join(days)
        
        # Create cron trigger
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute
        )
        
        # Add job
        scheduler.add_job(
            _alarm_trigger,
            trigger=trigger,
            id=ALARM_JOB_ID,
            replace_existing=True
        )
        
        print(f"[Alarm] Scheduled for {time_str} on {day_of_week}")
    
    return True


def reload_display_schedule() -> bool:
    """Reload the display wake schedule from config."""
    scheduler = get_scheduler()
    config = load_display_config()
    
    # Remove existing display wake job if present
    try:
        scheduler.remove_job(DISPLAY_WAKE_JOB_ID)
    except Exception:
        pass  # Job might not exist
    
    if not config.get("wake_enabled", True):
        print("[Display] Display wake is disabled")
        return True
    
    # Parse time
    time_str = config.get("wake_time", "07:00")
    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        print(f"[Display] Invalid time format: {time_str}")
        return False
    
    # Create cron trigger (every day)
    trigger = CronTrigger(
        hour=hour,
        minute=minute
    )
    
    # Add job
    scheduler.add_job(
        _display_wake_trigger,
        trigger=trigger,
        id=DISPLAY_WAKE_JOB_ID,
        replace_existing=True
    )
    
    print(f"[Display] Wake scheduled for {time_str} daily")
    return True


def _check_config_changed():
    """Check if config files have changed and reload if needed."""
    global _last_config_mtime, _last_display_config_mtime
    
    # Check alarm config
    try:
        if CONFIG_FILE.exists():
            current_mtime = os.path.getmtime(CONFIG_FILE)
            if current_mtime > _last_config_mtime:
                print("[Alarm] Config file changed, reloading schedule...")
                _last_config_mtime = current_mtime
                reload_schedule()
    except Exception as e:
        print(f"[Alarm] Error checking config: {e}")
    
    # Check display config
    try:
        if DISPLAY_CONFIG_FILE.exists():
            current_mtime = os.path.getmtime(DISPLAY_CONFIG_FILE)
            if current_mtime > _last_display_config_mtime:
                print("[Display] Config file changed, reloading schedule...")
                _last_display_config_mtime = current_mtime
                reload_display_schedule()
    except Exception as e:
        print(f"[Display] Error checking config: {e}")


def start_scheduler():
    """Start the scheduler."""
    global _last_config_mtime, _last_display_config_mtime
    
    scheduler = get_scheduler()
    
    if scheduler.running:
        return
    
    # Record initial config mtimes
    if CONFIG_FILE.exists():
        _last_config_mtime = os.path.getmtime(CONFIG_FILE)
    if DISPLAY_CONFIG_FILE.exists():
        _last_display_config_mtime = os.path.getmtime(DISPLAY_CONFIG_FILE)
    
    # Load schedules
    reload_schedule()
    reload_display_schedule()
    
    # Add periodic config check (every 10 seconds)
    scheduler.add_job(
        _check_config_changed,
        'interval',
        seconds=10,
        id=CONFIG_CHECK_JOB_ID,
        replace_existing=True
    )
    
    scheduler.start()
    print("[Alarm] Scheduler started (config auto-reload enabled)")


def stop_scheduler():
    """Stop the scheduler and any playing music."""
    global _scheduler
    
    stop_playback()
    
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Alarm] Scheduler stopped")
    
    _scheduler = None


def get_next_alarm_time() -> Optional[datetime]:
    """Get the next scheduled alarm time."""
    scheduler = get_scheduler()
    
    try:
        job = scheduler.get_job(ALARM_JOB_ID)
        if job and job.next_run_time:
            return job.next_run_time
    except Exception:
        pass
    
    return None
