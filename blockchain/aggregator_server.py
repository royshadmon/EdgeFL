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
    "http://localhost:8081"
  ],
  "config": {  
    "model": {
      "path": "/path/to/model"
    },
    "data": {
      "path": "/path/to/data"
    }
  },
  "contractAddress": "0x0222d3b0Be3A9E087f3a97104c1166bE05E2DEee"
}'
'''

@app.route('/deploy-contract', methods=['POST'])
def deploy_contract():
    """Deploy the smart contract with predefined nodes."""
    try:
        data = request.json
        node_addresses = data.get('nodeAddresses', [])
        node_urls = data.get('nodeUrls', [])
        config = data.get('config', {})
        contract_address = data.get('contractAddress')

        if not node_addresses:
            return jsonify({'status': 'error', 'message': 'No nodes provided'}), 400
        
        # Initialize the nodes and send the contract address
        print(f"Deploying contract with nodes: {node_addresses}")
        initialize_nodes(contract_address, node_urls, config)
        print("made it here")

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify(contract_address), 200
    


def initialize_nodes(contract_address, node_urls, config):
    """Send the deployed contract address to multiple node servers."""
    for url in node_urls:
        try:
            print(f"Sending contract address to node at {url}")
            response = requests.post(f'{url}/init-node', json={
                'contractAddress': contract_address,
                'config': config
            })

            #TODO: figure out how to handle response
            # I am assuming that the node initialization above will be successful without actually checking

            # if response.status_code == 200:
            #     print(f"Contract address successfully sent to node at {url}")
            # else:
            #     print(f"Failed to send contract address to {url}: {response.text}")

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
            newAggregatorParams = await listen_for_update_agg(min_params, r)
            print("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initialParams = newAggregatorParams

        return jsonify({'status': 'success', 'message': 'Training completed successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


async def listen_for_update_agg(min_params, roundNumber):
    """Asynchronously poll for the 'updateAggregatorWithParamsFromNodes' event from the blockchain."""
    print("Starting async polling for 'updateAggregatorWithParamsFromNodes' events...")

    count = 0

    while True:

        # curl: listen for enough params to be added
        headers = {
            "Content-Type": "text/plain",
            "command": f"blockchain get r{roundNumber} count",
        }

        response = requests.get(os.getenv("EXTERNAL_IP"), headers=headers)
        count = response; # response outputs just the number afaik

        if count == min_params:
            headers = {
                "Content-Type": "text/plain",
                "command": f"blockchain get r{roundNumber}",
            }

            response = requests.get(os.getenv("EXTERNAL_IP"), headers=headers)

            # need to figure out what response is later & how to handle
            return response
        
        # Asynchronously sleep to avoid excessive polling
        time.sleep(2)  # Poll every 2 seconds


if __name__ == '__main__':
    # Add argument parsing to make the port configurable
    parser = argparse.ArgumentParser(description="Run the Aggregator Server.")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on")
    args = parser.parse_args()

    # Run the Flask server on the provided port
    app.run(host='0.0.0.0', port=args.port)