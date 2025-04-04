#!/bin/bash

echo "Stopping blockchain servers..."

# Try graceful shutdown first
echo "Attempting severs shutdown..."
pkill -f "python blockchain/node_server.py"
pkill -f "python blockchain/aggregator_server.py"

# Wait a moment to let them shut down
sleep 2

# Check if any processes are still running
if pgrep -f "python blockchain/node_server.py" > /dev/null || pgrep -f "python blockchain/aggregator_server.py" > /dev/null; then
    echo "Some processes still running. Attempting force shutdown..."
    # Force kill if they're still running
    pkill -9 -f "python blockchain/node_server.py"
    pkill -9 -f "python blockchain/aggregator_server.py"
    sleep 1
fi

# Final check
if pgrep -f "python blockchain/node_server.py" > /dev/null || pgrep -f "python blockchain/aggregator_server.py" > /dev/null; then
    echo "Warning: Some processes could not be killed. You may need to investigate manually with 'ps aux | grep python'"
    exit 1
else
    echo "All blockchain servers successfully stopped"
fi