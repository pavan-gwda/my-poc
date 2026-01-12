#!/bin/bash
# Run Burnout Monitor as a background process
cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run in background
nohup python main.py > /dev/null 2>&1 &
echo "Burnout Monitor started!"
echo "PID: $!"
echo ""
echo "Look for the floating widget on your screen."
echo "Right-click widget for menu, double-click to start Pomodoro."
echo ""
echo "To stop: ./stop.sh"
