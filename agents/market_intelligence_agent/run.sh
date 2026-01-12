#!/bin/bash
cd "$(dirname "$0")"
nohup python3 main.py > /tmp/market_agent.log 2>&1 &
echo $! > .pid
echo "Started (PID: $!)"
echo "Logs: /tmp/market_agent.log"
