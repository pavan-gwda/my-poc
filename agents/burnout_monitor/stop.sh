#!/bin/bash
# Stop Burnout Monitor
pkill -f "burnout_monitor/main.py" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "Burnout Monitor stopped."
else
    echo "Burnout Monitor is not running."
fi
