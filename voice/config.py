"""Configuration for voice assistant."""

import os
from pathlib import Path

# Base paths
PROJECT_DIR = Path(__file__).parent.parent
MODELS_DIR = PROJECT_DIR / "models"

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1280  # 80ms at 16kHz - good for wake word detection

# Microphone - set to None for default, or specify device index
# Use `python -c "import sounddevice; print(sounddevice.query_devices())"` to list
AUDIO_INPUT_DEVICE = os.environ.get("AUDIO_DEVICE", None)  # None = default capture device
if AUDIO_INPUT_DEVICE is not None:
    AUDIO_INPUT_DEVICE = int(AUDIO_INPUT_DEVICE)

# Startup delay for systemd (wait for audio devices to be ready)
STARTUP_DELAY = float(os.environ.get("STARTUP_DELAY", "0"))

# Wake word settings
WAKE_WORD_MODEL = "hey_jarvis"
WAKE_WORD_THRESHOLD = 0.7  # Confidence threshold (0-1), higher = fewer false positives
WAKE_WORD_REFRACTORY = 2.0  # Seconds to wait after detection before listening again

# Speech-to-Text settings
# STT_ENGINE: "vosk" (fast, less accurate), "whisper" (slower, more accurate), 
#             or "moonshine" (fast AND accurate, best for Pi)
STT_ENGINE = os.environ.get("STT_ENGINE", "vosk")

# Vosk settings
VOSK_MODEL_PATH = str(MODELS_DIR / "vosk-model")

# Whisper settings (faster-whisper)
# Model sizes: tiny, base, small, medium, large
# For Raspberry Pi, use "tiny" or "base"
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
WHISPER_DEVICE = "cpu"  # Use "cuda" if you have NVIDIA GPU
WHISPER_COMPUTE_TYPE = "int8"  # Use "int8" for CPU, "float16" for GPU

# Moonshine settings (usefulsensors/moonshine)
# Model sizes: tiny (~36MB), base (~61MB)
# Designed for edge devices, 5x faster than Whisper with similar accuracy
MOONSHINE_MODEL = os.environ.get("MOONSHINE_MODEL", "moonshine/base")

# Piper TTS settings
PIPER_MODEL_PATH = str(MODELS_DIR / "piper" / "en_US-bryce-medium.onnx")

# Ollama settings (for intent fallback)
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen:0.5b"
OLLAMA_TIMEOUT = 30  # seconds
OLLAMA_ENABLED = False  # Disabled - small models are unreliable for intent parsing

# Flask API settings
API_BASE_URL = os.environ.get("HEALTH_API_URL", "http://localhost:5000")

# Voice activity detection
VAD_SILENCE_THRESHOLD = 1.5  # seconds of silence to stop recording
MAX_RECORDING_TIME = 4  # max seconds to record after wake word

# Debug settings
DEBUG = os.environ.get("VOICE_DEBUG", "0") == "1"
