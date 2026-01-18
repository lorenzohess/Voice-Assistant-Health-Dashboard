"""Display power control using wlopm (Wayland Output Power Management)."""

import subprocess
from typing import Optional


def display_on() -> bool:
    """
    Turn on the display.
    
    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ["wlopm", "--on", "*"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("[Display] Display turned ON")
            return True
        else:
            print(f"[Display] Failed to turn on: {result.stderr.decode()}")
            return False
    except FileNotFoundError:
        print("[Display] Error: wlopm not installed. Run: sudo apt install wlopm")
        return False
    except Exception as e:
        print(f"[Display] Error turning on display: {e}")
        return False


def display_off() -> bool:
    """
    Turn off the display.
    
    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ["wlopm", "--off", "*"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("[Display] Display turned OFF")
            return True
        else:
            print(f"[Display] Failed to turn off: {result.stderr.decode()}")
            return False
    except FileNotFoundError:
        print("[Display] Error: wlopm not installed. Run: sudo apt install wlopm")
        return False
    except Exception as e:
        print(f"[Display] Error turning off display: {e}")
        return False


def get_display_state() -> Optional[bool]:
    """
    Get current display power state.
    
    Returns True if on, False if off, None if unknown.
    """
    try:
        result = subprocess.run(
            ["wlopm"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # wlopm output format: "HDMI-A-1 on" or "HDMI-A-1 off"
            output = result.stdout.strip().lower()
            if " on" in output:
                return True
            elif " off" in output:
                return False
        return None
    except Exception:
        return None


def toggle_display() -> bool:
    """Toggle display power state."""
    state = get_display_state()
    if state is None:
        # Unknown state, try turning on
        return display_on()
    elif state:
        return display_off()
    else:
        return display_on()
