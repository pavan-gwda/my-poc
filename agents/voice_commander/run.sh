#!/bin/bash
cd "$(dirname "$0")"

# Use the same venv as speech_to_text_agent
VENV_PATH="../speech_to_text_agent/venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please run speech_to_text_agent setup first."
    exit 1
fi

# Check if already running
if [ -f .pid ] && kill -0 $(cat .pid) 2>/dev/null; then
    echo "Voice Commander is already running (PID: $(cat .pid))"
    exit 1
fi

mkdir -p logs

# Run in background using the venv
source "$VENV_PATH/bin/activate"
nohup python main.py > logs/output.log 2>&1 &
echo $! > .pid

echo "Voice Commander started!"
echo "PID: $(cat .pid)"
echo ""
echo "Hold Cmd+Alt (Option) and speak a command."
echo "Examples: 'Open Safari', 'Volume up', 'Search weather'"
echo ""
echo "To stop: ./stop.sh"
