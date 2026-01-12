#!/bin/bash
# Stop Speech-to-Text Agent
pkill -f "speech_to_text_agent/main.py" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "Speech-to-Text Agent stopped."
else
    echo "Speech-to-Text Agent is not running."
fi
