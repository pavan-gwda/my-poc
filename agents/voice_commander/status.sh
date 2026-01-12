#!/bin/bash
cd "$(dirname "$0")"

if [ -f .pid ] && kill -0 $(cat .pid) 2>/dev/null; then
    echo "Voice Commander is running (PID: $(cat .pid))"
else
    echo "Voice Commander is not running."
fi
