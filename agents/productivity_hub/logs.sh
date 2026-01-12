#!/bin/bash

# View Productivity Hub logs (live tail)

cd "$(dirname "$0")"

LOG_FILE=$(ls -t logs/*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "No log files found"
    exit 1
fi

echo "Viewing: $LOG_FILE"
echo "Press Ctrl+C to exit"
echo ""
tail -f "$LOG_FILE"
