#!/bin/bash
# Check Burnout Monitor status
PID=$(pgrep -f "burnout_monitor/main.py")

if [ -n "$PID" ]; then
    echo "Burnout Monitor is running (PID: $PID)"
else
    echo "Burnout Monitor is not running."
    echo "Start with: ./run.sh"
fi
