import argparse
from dotenv import load_dotenv

from flask import Flask, jsonify, request
from aggregator import Aggregator
import threading
import time
import requests
import os

app = Flask(__name__)
load_dotenv()

# Use environment variables for sensitive data
PROVIDER_URL = os.getenv('PROVIDER_URL')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

# Initialize the Aggregator instance
aggregator = Aggregator(PROVIDER_URL, PRIVATE_KEY)

'''
CURL REQUEST FOR DEPLOYING CONTRACT

curl -X POST http://localhost:8080/deploy-contract \
-H "Content-Type: application/json" \
-d '{
  "nodeAddresses": [
    "0xFEe882466e0804831746336A3eb2c6727CC35d63"
  ],
  "nodeUrls": [
    "http://localhost:8081", 
    "http://localhost:8082"
  ],
  "config": {  
    "model": {
      "path": "/path/to/model"
    },
    "data": {
      "path": "/path/to/data"
    }
  },
  "contractAddress": "0xF21E95f39Ac900986c4D47Bb17De767d80451e3B"
}'
'''
# CALL THIS ONLY IF I HAVE MADE UPDATES TO THE CONTRACT, IF I DO THEN CHANGE THE "CONTRACT_ADDRESS" GLOBAL VAR IN THE
# AGGREGATOR.PY FILE AND THE NODE_SERVER.PY FILE. IF NO UPDATES MADE, CALL THE INIT_NODE METHOD TO START THE NODE AND
# THEN CALL THE START ROUND ENDPOINT
@app.route('/deploy-contract', methods=['POST'])
def deploy_contract():
    """Deploy the smart contract with predefined nodes."""
    try:
        data = request.json
        node_addresses = data.get('nodeAddresses', [])
        node_urls = data.get('nodeUrls', [])
        config = data.get('config', {})
        # contract_address = data.get('contractAddress')

        if not node_addresses:
            return jsonify({'status': 'error', 'message': 'No nodes provided'}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def initialize_nodes(contract_address, node_urls, config):
    """Send the deployed contract address to multiple node servers."""
    for url in node_urls:
        try:
            response = requests.post(f'{url}/init-node', json={
                'contractAddress': contract_address,
                'config': config
            })
            if response.status_code == 200:
                print(f"Contract address successfully sent to node at {url}")
            else:
                print(f"Failed to send contract address to {url}: {response.text}")
        except Exception as e:
            print(f"Error sending contract address to {url}: {str(e)}")


'''
EXAMPLE CURL REQUEST FOR STARTING TRAINING

curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5, 
  "minParams": 1
}'
'''

@app.route('/start-training', methods=['POST'])
async def init_training():
    """Start the training process by setting the number of rounds."""
    try:
        data = request.json
        num_rounds = data.get('totalRounds', 1)
        min_params = data.get('minParams', 1)

        if num_rounds <= 0:
            return jsonify({'status': 'error', 'message': 'Invalid number of rounds'}), 400

        print(f"Training initialized with {num_rounds} rounds.")

        initialParams = ''

        for r in range(1, num_rounds + 1):
            print(f"Starting round {r}")
            aggregator.start_round(initialParams, r, min_params)

            # Listen for updates from nodes
            newAggregatorParams = await listen_for_update_agg(min_params)
            print("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initialParams = newAggregatorParams

        return jsonify({'status': 'success', 'message': 'Training completed successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


async def listen_for_update_agg(min_params):
    """Asynchronously poll for the 'updateAggregatorWithParamsFromNodes' event from the blockchain."""
    print("Starting async polling for 'updateAggregatorWithParamsFromNodes' events...")

    count = 0


    while count < min_params:

        # Make curl to egt Updates



        # Asynchronously sleep to avoid excessive polling
        time.sleep(2)  # Poll every 2 seconds


if __name__ == '__main__':
    # Add argument parsing to make the port configurable
    parser = argparse.ArgumentParser(description="Run the Aggregator Server.")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on")
    args = parser.parse_args()

    # Run the Flask server on the provided port
    app.run(host='0.0.0.0', port=args.port)