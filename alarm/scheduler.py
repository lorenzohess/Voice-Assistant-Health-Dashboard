"""Scheduler for alarm using APScheduler."""

import json
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import CONFIG_FILE
from .player import play_random_playlist, stop_playback

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None

# Job ID for the alarm
ALARM_JOB_ID = "morning_alarm"


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
        return True
    except IOError as e:
        print(f"[Alarm] Error saving config: {e}")
        return False


def _alarm_trigger():
    """Called when alarm triggers."""
    print(f"[Alarm] Alarm triggered at {datetime.now().strftime('%H:%M')}")
    play_random_playlist()


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
        return True
    
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


def start_scheduler():
    """Start the scheduler."""
    scheduler = get_scheduler()
    
    if scheduler.running:
        return
    
    reload_schedule()
    scheduler.start()
    print("[Alarm] Scheduler started")


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
