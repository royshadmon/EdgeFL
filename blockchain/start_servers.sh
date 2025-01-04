#!/bin/bash

# Kill existing Python processes for the blockchain servers
echo "Stopping existing servers..."
pkill -f "python node_server.py"
pkill -f "python aggregator_server.py"

# Wait a moment to ensure processes are terminated
sleep 2

# Check if any processes are still running
if pgrep -f "python3.9 node_server.py" > /dev/null || pgrep -f "python3.9 aggregator_server.py" > /dev/null; then
    echo "Warning: Some servers couldn't be stopped. You may need to kill them manually."
    echo "Use 'ps aux | grep python3.9' to check processes"
    exit 1
fi

# Start node server in background
echo "Starting node server..."
python3.9 node_server.py &

# Start second node server on different port
echo "Starting second node server..."
python3.9 node_server.py --p 8082 &

# Start aggregator server in background
echo "Starting aggregator server..."
python3.9 aggregator_server.py &

echo "Servers started successfully"
echo "Use 'ps aux | grep python3.9' to check running processes"