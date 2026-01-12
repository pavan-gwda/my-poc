#!/bin/bash
cd "$(dirname "$0")"
if [ -f .pid ]; then
    kill $(cat .pid) 2>/dev/null && echo "Stopped" || echo "Not running"
    rm -f .pid
else
    echo "Not running"
fi
