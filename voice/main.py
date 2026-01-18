#!/usr/bin/env python3
"""
Voice Assistant for Health Dashboard.

Usage:
    python -m voice.main           # Normal mode with wake word
    python -m voice.main --no-wake # Skip wake word (for testing)
    python -m voice.main --debug   # Enable debug output
"""

import argparse
import signal
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description="Health Dashboard Voice Assistant")
    parser.add_argument("--no-wake", action="store_true", help="Skip wake word detection")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--single", action="store_true", help="Process single command and exit")
    args = parser.parse_args()
    
    # Set debug mode before imports
    if args.debug:
        os.environ["VOICE_DEBUG"] = "1"
    
    # Now import modules (they read DEBUG from env)
    from voice.config import DEBUG, WAKE_WORD_MODEL
    from voice.listener import VoiceListener
    from voice.intent import parse_intent
    from voice.commands import execute_command
    from voice.tts import speak
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nShutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 50)
    print("Health Dashboard Voice Assistant")
    print("=" * 50)
    
    if args.no_wake:
        print("Wake word: DISABLED (test mode)")
    else:
        print(f"Wake word: '{WAKE_WORD_MODEL}'")
    
    print("Debug:", "ON" if DEBUG else "OFF")
    print()
    
    # Initialize listener
    print("Loading models...")
    try:
        listener = VoiceListener()
    except Exception as e:
        print(f"Failed to initialize listener: {e}")
        sys.exit(1)
    
    print("Ready! Listening...")
    if not args.no_wake:
        print(f"Say '{WAKE_WORD_MODEL}' to activate.")
    print()
    
    # Optional: play startup sound
    # speak("Voice assistant ready.")
    
    # Main loop
    while True:
        try:
            # Wait for wake word (unless disabled)
            if not args.no_wake:
                if not listener.wait_for_wake_word():
                    continue
                
                # Acknowledge wake word
                speak("Yes?")
            
            # Listen and transcribe
            text = listener.listen_and_transcribe()
            
            if not text:
                if args.no_wake:
                    print("No speech detected. Try again.")
                continue
            
            print(f"Heard: '{text}'")
            
            # Parse intent
            intent = parse_intent(text)
            
            if not intent:
                speak("Sorry, I didn't understand that.")
                if args.single:
                    break
                continue
            
            print(f"Intent: {intent.intent} -> {intent.params}")
            
            # Execute command
            result = execute_command(intent)
            
            print(f"Result: {'OK' if result.success else 'FAILED'} - {result.message}")
            
            # Speak result
            speak(result.message)
            
            if args.single:
                break
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
            speak("An error occurred.")
            
            if args.single:
                break
    
    print("\nGoodbye!")


if __name__ == "__main__":
    main()
