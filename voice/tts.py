"""Text-to-speech using Piper."""

import io
import os
import wave
import subprocess
from pathlib import Path

import numpy as np

from .config import PIPER_MODEL_PATH, DEBUG, PROJECT_DIR

# Directory for cached audio files
CACHE_DIR = PROJECT_DIR / "voice" / ".tts_cache"


class TextToSpeech:
    """Piper TTS wrapper with caching for common phrases."""

    # Common phrases to precompute
    COMMON_PHRASES = [
        "Ready!",  # Exclamation often sounds clearer than question
        "Yes!",  # Exclamation often sounds clearer than question
        "Sorry, I didn't understand that.",
        "An error occurred.",
        "Cannot connect to dashboard server.",
        "Done.",
        "OK.",
    ]

    def __init__(self, model_path: str = None, precompute: bool = True):
        self.model_path = model_path or PIPER_MODEL_PATH
        self.sample_rate = 22050  # Default, will be updated from config
        self._verify_model()
        self._load_config()
        self._cache = {}

        if precompute:
            self._precompute_common()

    def _verify_model(self):
        """Check that model files exist."""
        model_file = Path(self.model_path)
        json_file = model_file.with_suffix(".onnx.json")

        if not model_file.exists():
            raise FileNotFoundError(f"Piper model not found: {self.model_path}")
        if not json_file.exists():
            raise FileNotFoundError(f"Piper config not found: {json_file}")

    def _load_config(self):
        """Load sample rate from model config."""
        import json

        json_file = Path(self.model_path).with_suffix(".onnx.json")
        try:
            with open(json_file, "r") as f:
                config = json.load(f)
                self.sample_rate = config.get("audio", {}).get("sample_rate", 22050)
                if DEBUG:
                    print(f"[TTS] Model sample rate: {self.sample_rate}")
        except Exception as e:
            if DEBUG:
                print(f"[TTS] Could not load config, using default sample rate: {e}")

    def _get_cache_path(self, text: str) -> Path:
        """Get cache file path for a phrase.

        Includes model name in hash so switching voices auto-regenerates cache.
        """
        import hashlib

        # Include model path in hash so different voices have different caches
        model_name = Path(self.model_path).stem
        cache_key = f"{model_name}:{text}"
        text_hash = hashlib.md5(cache_key.encode()).hexdigest()[:16]
        return CACHE_DIR / f"{text_hash}.wav"

    def _precompute_common(self):
        """Precompute audio for common phrases."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        for phrase in self.COMMON_PHRASES:
            cache_path = self._get_cache_path(phrase)

            if not cache_path.exists():
                if DEBUG:
                    print(f"[TTS] Precomputing: '{phrase}'")
                self._synthesize_to_file(phrase, cache_path)

            self._cache[phrase] = cache_path

    def _synthesize_to_file(self, text: str, output_path: Path):
        """Synthesize text to a WAV file."""
        try:
            subprocess.run(
                f'echo "{text}" | piper --model {self.model_path} --output_file {output_path}',
                shell=True,
                check=True,
                capture_output=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as e:
            if DEBUG:
                print(f"[TTS] Synthesis error: {e.stderr.decode()}")

    def speak(self, text: str):
        """Synthesize and play text. Uses cache if available."""
        if DEBUG:
            print(f"[TTS] Speaking: {text}")

        # Check cache first
        cache_path = self._cache.get(text)
        if cache_path and cache_path.exists():
            self._play_cached(cache_path)
            return

        # Also check disk cache
        disk_cache = self._get_cache_path(text)
        if disk_cache.exists():
            self._play_cached(disk_cache)
            return

        # Synthesize on the fly
        try:
            # Use subprocess with pipes to avoid shell escaping issues
            piper_proc = subprocess.Popen(
                ["piper", "--model", str(self.model_path), "--output-raw"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            aplay_proc = subprocess.Popen(
                ["aplay", "-r", str(self.sample_rate), "-f", "S16_LE", "-t", "raw", "-q"],
                stdin=piper_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # Send text to piper
            piper_proc.stdin.write(text.encode())
            piper_proc.stdin.close()
            piper_proc.stdout.close()  # Allow aplay to receive EOF
            
            # Wait for completion
            aplay_proc.wait(timeout=30)
            piper_proc.wait(timeout=5)

            if piper_proc.returncode != 0 and DEBUG:
                print(f"[TTS] Piper warning: {piper_proc.stderr.read().decode()}")
            if aplay_proc.returncode != 0 and DEBUG:
                print(f"[TTS] Aplay warning: {aplay_proc.stderr.read().decode()}")

        except subprocess.TimeoutExpired:
            process.kill()
            if DEBUG:
                print("[TTS] Timeout during speech")
        except Exception as e:
            if DEBUG:
                print(f"[TTS] Error: {e}")

    def _play_cached(self, cache_path: Path):
        """Play a cached audio file."""
        try:
            subprocess.run(["aplay", "-q", str(cache_path)], check=True, timeout=10)
        except Exception as e:
            if DEBUG:
                print(f"[TTS] Playback error: {e}")

    def speak_async(self, text: str) -> subprocess.Popen:
        """Synthesize and play text without blocking."""
        if DEBUG:
            print(f"[TTS] Speaking (async): {text}")

        # Check cache
        cache_path = self._cache.get(text)
        if cache_path and cache_path.exists():
            return subprocess.Popen(
                ["aplay", "-q", str(cache_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        # Use a wrapper script approach for async
        # This is a bit hacky but avoids shell escaping issues
        import tempfile
        import os
        
        # Write text to temp file and speak from it
        fd, temp_path = tempfile.mkstemp(suffix='.txt')
        os.write(fd, text.encode())
        os.close(fd)
        
        return subprocess.Popen(
            f'cat "{temp_path}" | piper --model {self.model_path} --output-raw | aplay -r {self.sample_rate} -f S16_LE -t raw -q; rm -f "{temp_path}"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


# Singleton instance
_tts_instance = None


def get_tts() -> TextToSpeech:
    """Get or create TTS instance."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TextToSpeech()
    return _tts_instance


def speak(text: str):
    """Convenience function to speak text."""
    get_tts().speak(text)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        text = (
            " ".join(sys.argv[2:])
            if len(sys.argv) > 2
            else "Hello, I am your health dashboard assistant."
        )
        print(f"Testing TTS with: {text}")
        speak(text)
        print("Done.")
    else:
        print("Usage: python -m voice.tts --test [text]")
