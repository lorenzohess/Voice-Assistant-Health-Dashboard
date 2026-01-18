"""Text-to-speech using Piper."""

import io
import wave
import subprocess
from pathlib import Path

import numpy as np

from .config import PIPER_MODEL_PATH, DEBUG


class TextToSpeech:
    """Piper TTS wrapper."""
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path or PIPER_MODEL_PATH
        self._verify_model()
    
    def _verify_model(self):
        """Check that model files exist."""
        model_file = Path(self.model_path)
        json_file = model_file.with_suffix(".onnx.json")
        
        if not model_file.exists():
            raise FileNotFoundError(f"Piper model not found: {self.model_path}")
        if not json_file.exists():
            raise FileNotFoundError(f"Piper config not found: {json_file}")
    
    def speak(self, text: str):
        """Synthesize and play text."""
        if DEBUG:
            print(f"[TTS] Speaking: {text}")
        
        try:
            # Use piper CLI to synthesize and aplay to play
            # This is simpler and more reliable than Python bindings
            process = subprocess.Popen(
                f'echo "{text}" | piper --model {self.model_path} --output-raw | aplay -r 22050 -f S16_LE -t raw -',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            _, stderr = process.communicate(timeout=30)
            
            if process.returncode != 0 and DEBUG:
                print(f"[TTS] Warning: {stderr.decode()}")
                
        except subprocess.TimeoutExpired:
            process.kill()
            if DEBUG:
                print("[TTS] Timeout during speech")
        except Exception as e:
            if DEBUG:
                print(f"[TTS] Error: {e}")
    
    def speak_async(self, text: str) -> subprocess.Popen:
        """Synthesize and play text without blocking."""
        if DEBUG:
            print(f"[TTS] Speaking (async): {text}")
        
        return subprocess.Popen(
            f'echo "{text}" | piper --model {self.model_path} --output-raw | aplay -r 22050 -f S16_LE -t raw -',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
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
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Hello, I am your health dashboard assistant."
        print(f"Testing TTS with: {text}")
        speak(text)
        print("Done.")
    else:
        print("Usage: python -m voice.tts --test [text]")
