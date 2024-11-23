#!/bin/bash

# Configuration
AGGREGATOR_SCRIPT="/Users/camillegandotra/Desktop/Anylog-Edgelake-CSE115D/blockchain/aggregator_server.py"
NODE_SCRIPT="/Users/camillegandotra/Desktop/Anylog-Edgelake-CSE115D/blockchain/node_server.py"
LOG_FILE="node_servers.log"
BASE_ADDRESS="0xFEe882466e0804831746336A3eb2c6727CC35d63"

# Check if the required number of nodes is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <number_of_nodes>"
    exit 1
fi

NUM_NODES=$1

# Clear and initialize the log file
echo "Starting aggregator and $NUM_NODES nodes..." > "$LOG_FILE"

# Function to find an available port
find_available_port() {
    local port=$1
    while lsof -i :$port &>/dev/null; do
        port=$((port + 1))
    done
    echo $port
}

# Find an available port for the aggregator starting from 8080
AGGREGATOR_PORT=$(find_available_port 8080)

# Start the aggregator in a new terminal window
echo "Starting aggregator server on port $AGGREGATOR_PORT..."
osascript -e "tell application \"Terminal\" to do script \"python3 $AGGREGATOR_SCRIPT --port $AGGREGATOR_PORT\"" &
sleep 2  # Allow the aggregator to start
echo "Aggregator URL: http://localhost:$AGGREGATOR_PORT" >> "$LOG_FILE"

# Start nodes
NODE_ADDRESSES=()
NODE_URLS=()
for ((i=1; i<=NUM_NODES; i++)); do
    NODE_PORT=$(find_available_port $((AGGREGATOR_PORT + i)))  # Start nodes after aggregator port
    NODE_ADDRESS="${BASE_ADDRESS}_$i"

    echo "Starting Node $i on port $NODE_PORT with address $NODE_ADDRESS..."
    osascript -e "tell application \"Terminal\" to do script \"python3 $NODE_SCRIPT --port $NODE_PORT\"" &
    sleep 1  # Allow the node to start

    # Log details
    NODE_ADDRESSES+=("$NODE_ADDRESS")
    NODE_URLS+=("http://localhost:$NODE_PORT")
    echo "Node $i: URL=http://localhost:$NODE_PORT, Address=$NODE_ADDRESS" >> "$LOG_FILE"
done

# Register nodes with the aggregator
echo "Registering nodes with aggregator..."
curl -X POST http://localhost:$AGGREGATOR_PORT/deploy-contract \
-H "Content-Type: application/json" \
-d '{
  "nodeAddresses": '"$(jq -n --argjson arr "$(printf '%s\n' "${NODE_ADDRESSES[@]}" | jq -R . | jq -s .)" '$arr')"',
  "nodeUrls": '"$(jq -n --argjson arr "$(printf '%s\n' "${NODE_URLS[@]}" | jq -R . | jq -s .)" '$arr')"',
  "config": { "model": { "path": "/path/to/model" }, "data": { "path": "/path/to/data" } }
}'

echo "DEPLOYED CONTRACT" >> "$LOG_FILE"

# Log registration details
echo "Aggregator registered with nodes. Details logged in $LOG_FILE."

# Wait for user confirmation to start training
read -p "Press Enter to start training..."

# Start the training via curl
echo "Starting training via the aggregator..."
curl -X POST http://localhost:$AGGREGATOR_PORT/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5,
  "minParams": 1
}'

echo "Training initiated. Monitor the aggregator logs for progress."

# Wait for termination
read -p "Press Enter to terminate all servers..."

# Terminate all servers
osascript -e "tell application \"Terminal\" to do script \"pkill -f python3\""

echo "All servers have been terminated."
