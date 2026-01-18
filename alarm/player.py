"""Music player using mpv."""

import os
import signal
import subprocess
from pathlib import Path
from typing import Optional

from . import MUSIC_DIR

# Supported audio formats
AUDIO_EXTENSIONS = {".m4a", ".opus", ".mp3", ".wav", ".flac", ".ogg"}

# Global reference to current player process
_current_player: Optional[subprocess.Popen] = None


def get_music_files() -> list[Path]:
    """Get all music files from the music directory."""
    if not MUSIC_DIR.exists():
        return []
    
    files = []
    for ext in AUDIO_EXTENSIONS:
        files.extend(MUSIC_DIR.glob(f"*{ext}"))
    
    return sorted(files)


def play_random_playlist() -> bool:
    """
    Play a shuffled playlist of all music files.
    
    Returns True if playback started, False if no files or error.
    """
    global _current_player
    
    # Stop any existing playback
    stop_playback()
    
    music_files = get_music_files()
    if not music_files:
        print("[Alarm] No music files found in", MUSIC_DIR)
        return False
    
    print(f"[Alarm] Starting shuffled playlist with {len(music_files)} tracks")
    
    try:
        # mpv with shuffle, no video, and loop playlist
        _current_player = subprocess.Popen(
            [
                "mpv",
                "--no-video",
                "--shuffle",
                "--loop-playlist=inf",  # Loop forever until stopped
                "--",  # End of options
                str(MUSIC_DIR),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        print("[Alarm] Error: mpv not installed. Run: sudo apt install mpv")
        return False
    except Exception as e:
        print(f"[Alarm] Error starting playback: {e}")
        return False


def stop_playback() -> bool:
    """
    Stop current music playback.
    
    Returns True if stopped, False if nothing was playing.
    """
    global _current_player
    
    if _current_player is None:
        return False
    
    try:
        # Send SIGTERM for graceful shutdown
        _current_player.terminate()
        _current_player.wait(timeout=2)
    except subprocess.TimeoutExpired:
        # Force kill if it doesn't respond
        _current_player.kill()
        _current_player.wait()
    except Exception as e:
        print(f"[Alarm] Error stopping playback: {e}")
    
    _current_player = None
    print("[Alarm] Playback stopped")
    return True


def is_playing() -> bool:
    """Check if music is currently playing."""
    global _current_player
    
    if _current_player is None:
        return False
    
    # Check if process is still running
    return _current_player.poll() is None


def get_player_pid() -> Optional[int]:
    """Get the PID of the current player process."""
    global _current_player
    
    if _current_player is None or _current_player.poll() is not None:
        return None
    
    return _current_player.pid
