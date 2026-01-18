"""Audio capture, wake word detection, and speech-to-text."""

import json
import time
import numpy as np
import sounddevice as sd
from openwakeword.model import Model as WakeWordModel

from .config import (
    SAMPLE_RATE,
    CHANNELS,
    CHUNK_SIZE,
    AUDIO_INPUT_DEVICE,
    WAKE_WORD_MODEL,
    WAKE_WORD_THRESHOLD,
    WAKE_WORD_REFRACTORY,
    STT_ENGINE,
    VOSK_MODEL_PATH,
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    MOONSHINE_MODEL,
    VAD_SILENCE_THRESHOLD,
    MAX_RECORDING_TIME,
    DEBUG,
)


class VoiceListener:
    """Handles wake word detection and speech-to-text."""
    
    def __init__(self):
        self.sample_rate = SAMPLE_RATE
        self.chunk_size = CHUNK_SIZE
        self.last_wake_time = 0  # For refractory period
        self.stt_engine = STT_ENGINE.lower()
        
        # Load wake word model
        if DEBUG:
            print("[Listener] Loading wake word model...")
        self.wake_model = WakeWordModel(wakeword_models=[WAKE_WORD_MODEL])
        
        # Load STT model based on config
        self.vosk_model = None
        self.whisper_model = None
        self.moonshine_model = None
        
        if self.stt_engine == "whisper":
            if DEBUG:
                print(f"[Listener] Loading Whisper model ({WHISPER_MODEL_SIZE})...")
            from faster_whisper import WhisperModel
            self.whisper_model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
        elif self.stt_engine == "moonshine":
            if DEBUG:
                print(f"[Listener] Loading Moonshine model ({MOONSHINE_MODEL})...")
            from moonshine_onnx import MoonshineOnnxModel
            self.moonshine_model = MoonshineOnnxModel(model_name=MOONSHINE_MODEL)
        else:
            if DEBUG:
                print("[Listener] Loading Vosk model...")
            from vosk import Model
            self.vosk_model = Model(VOSK_MODEL_PATH)
        
        if DEBUG:
            print(f"[Listener] Models loaded. STT engine: {self.stt_engine}")
    
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
        # Enforce refractory period
        time_since_last = time.time() - self.last_wake_time
        if time_since_last < WAKE_WORD_REFRACTORY:
            wait_time = WAKE_WORD_REFRACTORY - time_since_last
            if DEBUG:
                print(f"[Listener] Refractory period, waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        # Reset the model's internal state to avoid lingering high scores
        self.wake_model.reset()
        
        if DEBUG:
            print(f"[Listener] Listening for wake word '{WAKE_WORD_MODEL}' (threshold: {WAKE_WORD_THRESHOLD})...")
        
        frame_count = 0
        
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
                    
                    # OpenWakeWord expects int16 audio, flattened
                    audio_int16 = audio_data.flatten()
                    
                    # Check for wake word
                    prediction = self.wake_model.predict(audio_int16)
                    
                    frame_count += 1
                    
                    # Debug: show predictions periodically
                    if DEBUG and frame_count % 50 == 0:  # Every ~4 seconds
                        max_conf = max(prediction.values()) if prediction else 0
                        if max_conf > 0.1:  # Only show if there's some activity
                            print(f"[Listener] Predictions: {prediction}")
                    
                    # Check all model predictions
                    for model_name, confidence in prediction.items():
                        if confidence > WAKE_WORD_THRESHOLD:
                            if DEBUG:
                                print(f"[Listener] Wake word detected: {model_name} ({confidence:.2f})")
                            self.last_wake_time = time.time()
                            return True
                            
        except KeyboardInterrupt:
            return False
        except Exception as e:
            if DEBUG:
                print(f"[Listener] Error in wake word detection: {e}")
                import traceback
                traceback.print_exc()
            return False
    
    def listen_and_transcribe(self) -> str:
        """
        Record audio until silence, then transcribe.
        Returns transcribed text or empty string on error.
        """
        if self.stt_engine == "whisper":
            return self._transcribe_whisper()
        elif self.stt_engine == "moonshine":
            return self._transcribe_moonshine()
        else:
            return self._transcribe_vosk()
    
    def _transcribe_vosk(self) -> str:
        """Transcribe using Vosk (streaming, faster but less accurate)."""
        if DEBUG:
            print("[Listener] Listening for speech (Vosk)...")
        
        from vosk import KaldiRecognizer
        recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
        
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
                print(f"[Listener] Error in Vosk transcription: {e}")
            return ""
    
    def _transcribe_whisper(self) -> str:
        """Transcribe using Whisper (batch, slower but more accurate)."""
        if DEBUG:
            print("[Listener] Listening for speech (Whisper)...")
        
        audio_chunks = []
        silence_start = None
        recording_start = time.time()
        has_speech = False
        
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
                    audio_chunks.append(audio_data.flatten())
                    
                    # Check for silence (simple energy-based VAD)
                    energy = np.abs(audio_data).mean()
                    is_silent = energy < 500
                    
                    if not is_silent:
                        has_speech = True
                        silence_start = None
                    elif has_speech:
                        # Only start silence timer after we've heard speech
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > VAD_SILENCE_THRESHOLD:
                            # Long silence after speech - stop recording
                            break
                    
                    # Max recording time
                    if time.time() - recording_start > MAX_RECORDING_TIME:
                        if DEBUG:
                            print("[Listener] Max recording time reached")
                        break
            
            if not audio_chunks or not has_speech:
                if DEBUG:
                    print("[Listener] No speech detected")
                return ""
            
            # Concatenate and convert to float32 for Whisper
            audio_array = np.concatenate(audio_chunks)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            if DEBUG:
                duration = len(audio_float) / self.sample_rate
                print(f"[Listener] Transcribing {duration:.1f}s of audio...")
            
            # Transcribe with Whisper
            segments, info = self.whisper_model.transcribe(
                audio_float,
                language="en",
                beam_size=1,  # Faster
                vad_filter=True,  # Filter out non-speech
            )
            
            # Combine all segments
            text = " ".join(segment.text.strip() for segment in segments).strip()
            
            if DEBUG:
                print(f"[Listener] Transcribed: {text}")
            
            return text
            
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            if DEBUG:
                print(f"[Listener] Error in Whisper transcription: {e}")
                import traceback
                traceback.print_exc()
            return ""
    
    def _transcribe_moonshine(self) -> str:
        """Transcribe using Moonshine (fast and accurate, optimized for edge devices)."""
        if DEBUG:
            print("[Listener] Listening for speech (Moonshine)...")
        
        audio_chunks = []
        silence_start = None
        recording_start = time.time()
        has_speech = False
        
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
                    audio_chunks.append(audio_data.flatten())
                    
                    # Check for silence (simple energy-based VAD)
                    energy = np.abs(audio_data).mean()
                    is_silent = energy < 500
                    
                    if not is_silent:
                        has_speech = True
                        silence_start = None
                    elif has_speech:
                        # Only start silence timer after we've heard speech
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > VAD_SILENCE_THRESHOLD:
                            # Long silence after speech - stop recording
                            break
                    
                    # Max recording time
                    if time.time() - recording_start > MAX_RECORDING_TIME:
                        if DEBUG:
                            print("[Listener] Max recording time reached")
                        break
            
            if not audio_chunks or not has_speech:
                if DEBUG:
                    print("[Listener] No speech detected")
                return ""
            
            # Concatenate and convert to float32 for Moonshine
            audio_array = np.concatenate(audio_chunks)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            if DEBUG:
                duration = len(audio_float) / self.sample_rate
                print(f"[Listener] Transcribing {duration:.1f}s of audio with Moonshine...")
            
            # Transcribe with Moonshine (expects 2D: batch x samples)
            audio_batch = audio_float[np.newaxis, :]
            text = self.moonshine_model.generate(audio_batch)
            
            # Handle if result is a list
            if isinstance(text, list):
                text = " ".join(text)
            
            text = text.strip() if text else ""
            
            if DEBUG:
                print(f"[Listener] Transcribed: {text}")
            
            return text
            
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            if DEBUG:
                print(f"[Listener] Error in Moonshine transcription: {e}")
                import traceback
                traceback.print_exc()
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
        print(f"Testing wake word detection. Say 'Hey Jarvis'...")
        
        # Force debug mode for this test
        import voice.config as cfg
        cfg.DEBUG = True
        
        listener = VoiceListener()
        print(f"Loaded models: {list(listener.wake_model.models.keys())}")
        print(f"Threshold: {WAKE_WORD_THRESHOLD}")
        print("Listening... (Ctrl+C to stop)")
        
        if listener.wait_for_wake_word():
            print("\n*** Wake word detected! ***")
        else:
            print("\nNo wake word detected or error.")
    
    elif "--test-wake-raw" in sys.argv:
        # Raw test without our wrapper
        print("Raw OpenWakeWord test...")
        from openwakeword.model import Model as WakeWordModel
        
        model = WakeWordModel(wakeword_models=['hey_jarvis'])
        print(f"Model keys: {list(model.models.keys())}")
        
        print("Listening for 'Hey Jarvis' (15 seconds)...")
        print("Shows audio level and prediction confidence")
        print()
        
        frame_count = 0
        max_prediction = 0
        
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='int16',
            blocksize=CHUNK_SIZE,
        ) as stream:
            start = time.time()
            while time.time() - start < 15:
                audio_data, _ = stream.read(CHUNK_SIZE)
                
                # Check audio level
                audio_level = np.abs(audio_data).mean()
                
                # OpenWakeWord expects int16 audio, flattened
                audio_int16 = audio_data.flatten()
                
                pred = model.predict(audio_int16)
                conf = pred.get('hey_jarvis', 0)
                max_prediction = max(max_prediction, conf)
                
                frame_count += 1
                
                # Show status every 10 frames (~0.8 seconds)
                if frame_count % 10 == 0:
                    bars = int(audio_level / 200)
                    pred_bars = int(conf * 50)
                    print(f"\rAudio: {'█' * min(bars, 30):30s} ({audio_level:5.0f}) | "
                          f"Wake: {'█' * pred_bars:25s} ({conf:.3f})", end="", flush=True)
                
                if conf > 0.5:
                    print(f"\n\n*** DETECTED! Confidence: {conf:.3f} ***")
                    break
        
        print(f"\n\nDone. Max prediction seen: {max_prediction:.3f}")
        if max_prediction < 0.01:
            print("\nTroubleshooting:")
            print("  - Max prediction near 0 suggests audio may not be reaching the model")
            print("  - Check that microphone is working: python -m voice.listener --test-mic")
            print("  - Try speaking louder or closer to the mic")
            
    elif "--test-stt" in sys.argv:
        print(f"Testing speech-to-text with {STT_ENGINE}. Speak now...")
        listener = VoiceListener()
        text = listener.listen_and_transcribe()
        print(f"Transcribed: '{text}'")
        
    else:
        print("Usage:")
        print("  python -m voice.listener --test-mic   # Test microphone levels")
        print("  python -m voice.listener --test-wake  # Test wake word detection")
        print("  python -m voice.listener --test-stt   # Test speech-to-text")
        print()
        print("Environment variables:")
        print(f"  STT_ENGINE={STT_ENGINE} (vosk, whisper, or moonshine)")
        print(f"  WHISPER_MODEL={WHISPER_MODEL_SIZE} (tiny, base, small, medium)")
        print(f"  MOONSHINE_MODEL={MOONSHINE_MODEL} (moonshine/tiny, moonshine/base)")
        print()
        print("Examples:")
        print("  STT_ENGINE=whisper python -m voice.listener --test-stt")
        print("  STT_ENGINE=moonshine python -m voice.listener --test-stt")
        print("  STT_ENGINE=moonshine python -m voice.main --debug")