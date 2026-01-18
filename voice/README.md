# Voice Assistant

The Health Dashboard voice assistant allows hands-free data entry using natural language commands.

## Setup

### STT Engine Options

Set the `STT_ENGINE` environment variable to choose your speech-to-text engine:

| Engine | Speed | Accuracy | Install |
|--------|-------|----------|---------|
| `vosk` | Real-time | Good | `pip install vosk` + download model |
| `whisper` | 4-6s delay | Excellent | `pip install faster-whisper` |
| `moonshine` | 1-2s delay | Excellent | See below |

**Moonshine (Recommended for Raspberry Pi):**
```bash
pip install useful-moonshine-onnx@git+https://github.com/usefulsensors/moonshine.git#subdirectory=moonshine-onnx
```

### Running

```bash
# With default Vosk
python -m voice.main --debug

# With Moonshine (recommended)
STT_ENGINE=moonshine python -m voice.main --debug

# With Whisper
STT_ENGINE=whisper python -m voice.main --debug
```

## Voice Commands

Say "Hey Jarvis" to activate, then speak one of the following commands.

### Calories

Log calories directly:
- "Add 500 calories"
- "Had 300 calories"
- "Ate 450 calories"
- "Logged 200 calories"

Log food with calories:
- "Add eggs 140 calories"
- "Had toast 120 calories"

Log food by quantity (requires food in database):
- "Add 2 servings of peanut butter"
- "Had 100 grams of chicken"
- "Ate 1 cup of rice"

### Weight

- "My weight is 75 kilos"
- "Weight 165 pounds"
- "I weigh 70 kg"
- "Weighed 150 lbs"

### Sleep

Simple hours:
- "I slept 8 hours"
- "Slept 7 hours"
- "Got 6 hours of sleep"

With fractions:
- "I slept 7 and a half hours"
- "Slept 8 and a quarter hours"
- "I slept 6 and three quarter hours"
- "Got 7.5 hours of sleep"

### Wake Time

With numbers:
- "I woke up at 7 AM"
- "Woke up at 7:30 AM"
- "I woke at 8 PM"

With words:
- "I woke up at seven thirty AM"
- "Woke up at eight fifteen AM"
- "I woke at six forty-five"

### Workouts

- "I worked out for 30 minutes"
- "Worked out 45 minutes"
- "Exercised for 60 minutes"
- "Did a workout for 20 minutes"
- "30 minute workout"

### Vegetables

- "Vegetables 3 servings"
- "Vegetables, 5 servings"
- "Vegetables 2"

### Custom Metrics

Any custom metric with a `voice_keyword` set can be logged:
- "[keyword] [number]"

Example: If you create a metric with voice_keyword "medication":
- "Medication 2"
- "Medication 1"

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STT_ENGINE` | `vosk` | STT engine: `vosk`, `whisper`, or `moonshine` |
| `WHISPER_MODEL` | `base` | Whisper model: `tiny`, `base`, `small`, `medium` |
| `MOONSHINE_MODEL` | `moonshine/base` | Moonshine model: `moonshine/tiny`, `moonshine/base` |
| `VOICE_DEBUG` | `0` | Set to `1` for debug output |
| `HEALTH_API_URL` | `http://localhost:5000` | Dashboard API URL |

## Testing

```bash
# Test microphone levels
python -m voice.listener --test-mic

# Test wake word detection
python -m voice.listener --test-wake

# Test speech-to-text
python -m voice.listener --test-stt

# Test with specific engine
STT_ENGINE=moonshine python -m voice.listener --test-stt
```

## Troubleshooting

### Wake word not detecting
- Check microphone levels: `python -m voice.listener --test-mic`
- Speak closer to the microphone
- Adjust `WAKE_WORD_THRESHOLD` in `config.py` (lower = more sensitive)

### Transcription inaccurate
- Try a different STT engine (moonshine recommended)
- Speak more clearly and slowly
- Reduce background noise

### Command not recognized
- Check debug output for what was transcribed
- Verify the command matches one of the patterns above
- Custom metrics need `voice_keyword` set in the database
