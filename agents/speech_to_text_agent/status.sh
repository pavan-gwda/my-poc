#!/bin/bash
# Check Speech-to-Text Agent status
PID=$(pgrep -f "speech_to_text_agent/main.py")

if [ -n "$PID" ]; then
    echo "Speech-to-Text Agent is running (PID: $PID)"
else
    echo "Speech-to-Text Agent is not running."
    echo "Start with: ./run.sh"
fi
