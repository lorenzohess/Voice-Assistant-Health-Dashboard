"""Main entry point for the alarm service."""

import signal
import sys
import time

from .scheduler import start_scheduler, stop_scheduler, load_config
from .player import stop_playback
from .hardware import HardwareController


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n[Alarm] Shutting down...")
    stop_scheduler()
    sys.exit(0)


# Global hardware controller reference for signal handler
_hardware: HardwareController = None


def _on_stop_button():
    """Callback when physical stop button is pressed."""
    print("[Alarm] Stop button triggered")
    stop_playback()


def main():
    """Main entry point."""
    global _hardware
    
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
    
    # Initialize hardware controller (button + volume pot)
    _hardware = HardwareController(on_button_press=_on_stop_button)
    if _hardware.is_available:
        _hardware.start()
        print("Hardware controls active (button: GPIO 17, volume: ADS1115 A0)")
    else:
        print("Hardware controls not available (software-only mode)")
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
        if _hardware is not None:
            _hardware.stop()
        stop_scheduler()


if __name__ == "__main__":
    main()
