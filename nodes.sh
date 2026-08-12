#!/bin/zsh

BASE_DIR="/Users/juan/Desktop/EdgeFL"
EDGEFL_DIR="$BASE_DIR/edgefl"
PYTHON="/opt/homebrew/bin/python3.11"
SCRIPT="$EDGEFL_DIR/platform_components/node/node_server.py"
AGG="$EDGEFL_DIR/platform_components/aggregator/aggregator_server.py"
ENV_DIR="$EDGEFL_DIR/env_files/mnist-docker"

SESSION=$(tmux display-message -p '#S')
RUN="cd $EDGEFL_DIR && set -a && source"
PYRUN="set +a && PYTHONUNBUFFERED=1 PYTHONPATH=$EDGEFL_DIR $PYTHON"

# Window 1: operators
# WINDOW=$(tmux new-window -t $SESSION -n "operators" -P -F "#{window_index}")
# Window 1: operators ---------------------------------------------------------
# new-window returns the pane_id of its single starting pane
P0=$(tmux new-window -t $SESSION -n "operators" -P -F "#{pane_id}")
OPS_WIN=$(tmux display-message -p -t $P0 '#{window_id}')
tmux send-keys -t $P0 "$RUN $ENV_DIR/mnist1.env && $PYRUN $SCRIPT --p 8081" Enter

# operator2: split P0 horizontally -> new pane id
P1=$(tmux split-window -v -t $P0 -P -F "#{pane_id}")
tmux send-keys -t $P1 "$RUN $ENV_DIR/mnist2.env && $PYRUN $SCRIPT --p 8082" Enter

# operator3: split P0 vertically -> new pane id
P2=$(tmux split-window -v -t $P1 -P -F "#{pane_id}")
tmux send-keys -t $P2 "$RUN $ENV_DIR/mnist3.env && $PYRUN $SCRIPT --p 8083" Enter

# tmux select-layout -t $P0 tiled

# Window 2: aggregator --------------------------------------------------------
AGG_PANE=$(tmux new-window -t $SESSION -n "aggregator" -P -F "#{pane_id}")
AGG_WIN=$(tmux display-message -p -t $AGG_PANE '#{window_id}')
tmux send-keys -t $AGG_PANE "$RUN $ENV_DIR/mnist-agg.env && $PYRUN $AGG --p 8080" Enter

# Cleanup on Ctrl+C / termination ---------------------------------------------
cleanup() {
  echo "\nShutting down — killing windows..."
  tmux kill-window -t $OPS_WIN 2>/dev/null
  tmux kill-window -t $AGG_WIN 2>/dev/null
  exit 0
}
trap cleanup INT TERM

echo "Nodes + aggregator launched. Press Ctrl+C here to kill both windows."
while true; do sleep 1; done
