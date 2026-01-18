"""Audio capture, wake word detection, and speech-to-text."""

import json
import time
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from openwakeword.model import Model as WakeWordModel

from .config import (
    SAMPLE_RATE,
    CHANNELS,
    CHUNK_SIZE,
    AUDIO_INPUT_DEVICE,
    WAKE_WORD_MODEL,
    WAKE_WORD_THRESHOLD,
    VOSK_MODEL_PATH,
    VAD_SILENCE_THRESHOLD,
    MAX_RECORDING_TIME,
    DEBUG,
)


class VoiceListener:
    """Handles wake word detection and speech-to-text."""
    
    def __init__(self):
        self.sample_rate = SAMPLE_RATE
        self.chunk_size = CHUNK_SIZE
        
        # Load models
        if DEBUG:
            print("[Listener] Loading wake word model...")
        self.wake_model = WakeWordModel(wakeword_models=[WAKE_WORD_MODEL])
        
        if DEBUG:
            print("[Listener] Loading Vosk model...")
        self.vosk_model = Model(VOSK_MODEL_PATH)
        
        if DEBUG:
            print("[Listener] Models loaded.")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status and DEBUG:
            print(f"[Listener] Audio status: {status}")
        self._audio_buffer.append(indata.copy())
    
    def wait_for_wake_word(self) -> bool:
        """
        Listen for wake word. Blocks until detected.
        Returns True if wake word detected, False on error.
        """
        if DEBUG:
            print(f"[Listener] Listening for wake word '{WAKE_WORD_MODEL}'...")
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype='int16',
                blocksize=self.chunk_size,
                device=AUDIO_INPUT_DEVICE,
            ) as stream:
                while True:
                    audio_data, _ = stream.read(self.chunk_size)
                    
                    # Convert to float32 for wake word model
                    audio_float = audio_data.flatten().astype(np.float32) / 32768.0
                    
                    # Check for wake word
                    prediction = self.wake_model.predict(audio_float)
                    
                    for wake_word, confidence in prediction.items():
                        if confidence > WAKE_WORD_THRESHOLD:
                            if DEBUG:
                                print(f"[Listener] Wake word detected: {wake_word} ({confidence:.2f})")
                            return True
                            
        except KeyboardInterrupt:
            return False
        except Exception as e:
            if DEBUG:
                print(f"[Listener] Error in wake word detection: {e}")
            return False
    
    def listen_and_transcribe(self) -> str:
        """
        Record audio until silence, then transcribe.
        Returns transcribed text or empty string on error.
        """
        if DEBUG:
            print("[Listener] Listening for speech...")
        
        recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
        
        audio_chunks = []
        silence_start = None
        recording_start = time.time()
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype='int16',
                blocksize=self.chunk_size,
                device=AUDIO_INPUT_DEVICE,
            ) as stream:
                while True:
                    audio_data, _ = stream.read(self.chunk_size)
                    audio_bytes = audio_data.tobytes()
                    
                    # Feed to recognizer
                    if recognizer.AcceptWaveform(audio_bytes):
                        # Got a complete phrase
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            if DEBUG:
                                print(f"[Listener] Transcribed: {text}")
                            return text
                    
                    # Check for silence (simple energy-based VAD)
                    energy = np.abs(audio_data).mean()
                    is_silent = energy < 500  # Adjust threshold as needed
                    
                    if is_silent:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > VAD_SILENCE_THRESHOLD:
                            # Long silence - get final result
                            result = json.loads(recognizer.FinalResult())
                            text = result.get("text", "").strip()
                            if DEBUG:
                                print(f"[Listener] Final transcription: {text}")
                            return text
                    else:
                        silence_start = None
                    
                    # Max recording time
                    if time.time() - recording_start > MAX_RECORDING_TIME:
                        result = json.loads(recognizer.FinalResult())
                        text = result.get("text", "").strip()
                        if DEBUG:
                            print(f"[Listener] Max time reached. Transcription: {text}")
                        return text
                        
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            if DEBUG:
                print(f"[Listener] Error in transcription: {e}")
            return ""
    
    def listen_once(self, skip_wake_word: bool = False) -> str:
        """
        Wait for wake word (unless skipped), then transcribe speech.
        Returns transcribed text.
        """
        if not skip_wake_word:
            if not self.wait_for_wake_word():
                return ""
        
        return self.listen_and_transcribe()


# Singleton instance
_listener_instance = None


def get_listener() -> VoiceListener:
    """Get or create listener instance."""
    global _listener_instance
    if _listener_instance is None:
        _listener_instance = VoiceListener()
    return _listener_instance


if __name__ == "__main__":
    import sys
    
    if "--test-mic" in sys.argv:
        print("Testing microphone (5 seconds)...")
        print("Speak and watch the levels:")
        
        def callback(indata, frames, time_info, status):
            energy = np.abs(indata).mean()
            bars = int(energy / 100)
            print(f"\rLevel: {'█' * bars}{' ' * (50 - bars)} ({energy:.0f})", end="", flush=True)
        
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='int16',
            blocksize=CHUNK_SIZE,
            callback=callback,
        ):
            time.sleep(5)
        print("\nDone.")
        
    elif "--test-wake" in sys.argv:
        print(f"Testing wake word detection. Say '{WAKE_WORD_MODEL}'...")
        listener = VoiceListener()
        if listener.wait_for_wake_word():
            print("Wake word detected!")
        else:
            print("No wake word detected or error.")
            
    elif "--test-stt" in sys.argv:
        print("Testing speech-to-text. Speak now...")
        listener = VoiceListener()
        text = listener.listen_and_transcribe()
        print(f"Transcribed: '{text}'")
        
    else:
        print("Usage:")
        print("  python -m voice.listener --test-mic   # Test microphone levels")
        print("  python -m voice.listener --test-wake  # Test wake word detection")
        print("  python -m voice.listener --test-stt   # Test speech-to-text")
