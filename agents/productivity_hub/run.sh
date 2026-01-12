#!/bin/bash

# Productivity Hub - Unified Agent
# Run script using the shared venv from speech_to_text_agent

cd "$(dirname "$0")"

# Use venv from speech_to_text_agent
source ../speech_to_text_agent/venv/bin/activate

# Run as background process
nohup python main.py > /dev/null 2>&1 &

echo "Productivity Hub started (PID: $!)"
echo "Logs: $(pwd)/logs/"
echo ""
echo "Hotkeys:"
echo "  Right Shift - Speech-to-Text (hold)"
echo "  Option key  - Voice Commander (hold)"
echo "  Double-click widget - Start/Stop Pomodoro"
echo ""
echo "To stop: pkill -f 'python main.py' or right-click widget → Quit"
