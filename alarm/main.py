"""Main entry point for the alarm service."""

import signal
import sys
import time

from .scheduler import start_scheduler, stop_scheduler, load_config
from .player import stop_playback


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n[Alarm] Shutting down...")
    stop_scheduler()
    sys.exit(0)


def main():
    """Main entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 50)
    print("Health Dashboard Alarm Service")
    print("=" * 50)
    
    config = load_config()
    print(f"Alarm time: {config.get('time', '08:00')}")
    print(f"Enabled: {config.get('enabled', True)}")
    print(f"Days: {', '.join(config.get('days', []))}")
    print()
    
    # Start the scheduler
    start_scheduler()
    
    print("Alarm service running. Press Ctrl+C to stop.")
    
    # Keep running
    try:
        while True:
            time.sleep(60)  # Sleep for a minute at a time
    except KeyboardInterrupt:
        pass
    finally:
        stop_scheduler()


if __name__ == "__main__":
    main()
