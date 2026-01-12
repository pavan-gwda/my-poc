#!/bin/bash
# Run Speech-to-Text Agent as background process
cd "$(dirname "$0")"
source venv/bin/activate
nohup python main.py > /dev/null 2>&1 &
echo "Speech-to-Text Agent started!"
echo "PID: $!"
echo ""
echo "Look for the floating widget on your screen."
echo "Hold Cmd+Shift to record, release to transcribe."
echo ""
echo "To stop: ./stop.sh"
