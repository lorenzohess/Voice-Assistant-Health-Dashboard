#!/bin/bash
# Play a very quiet, short tone to keep the speaker from auto-shutting off
# Runs via cron every 25 minutes

# Generate and play a 0.1 second, very quiet 440Hz tone
# Volume is set extremely low (0.01 = 1% amplitude)
# paplay --volume=1000 <(sox -n -r 44100 -c 2 -t wav - synth 0.1 sine 440 vol 0.01) 2>/dev/null

# Alternative if sox/paplay don't work - use speaker-test for 0.1 seconds
# Send SIGKILL (9) after 3 seconds
timeout -s 9 3 speaker-test -t sine -f 20 -l 1 >/dev/null 2>&1
