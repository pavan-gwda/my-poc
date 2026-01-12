#!/bin/bash
cd "$(dirname "$0")"

if [ -f .pid ]; then
    PID=$(cat .pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        rm .pid
        echo "Voice Commander stopped."
    else
        rm .pid
        echo "Voice Commander was not running."
    fi
else
    echo "Voice Commander is not running."
fi
