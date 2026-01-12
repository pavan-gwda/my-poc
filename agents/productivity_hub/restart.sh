#!/bin/bash

# Productivity Hub - Restart script

cd "$(dirname "$0")"

echo "Restarting Productivity Hub..."

# Stop existing process
pkill -f "python main.py" 2>/dev/null
sleep 1

# Run again
./run.sh