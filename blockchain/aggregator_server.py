from flask import Flask, jsonify, request
from aggregator import Aggregator
import threading
import time
import requests
import os

app = Flask(__name__)


# Use environment variables for sensitive data
PROVIDER_URL = os.getenv('PROVIDER_URL', 'https://optimism-sepolia.infura.io/v3/524787abec0740b9a443cb825966c31e')
PRIVATE_KEY = os.getenv('PRIVATE_KEY', 'f155acda1fc73fa6f50456545e3487b78fd517411708ffa1f67358c1d3d54977')

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
  }
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

        if not node_addresses:
            return jsonify({'status': 'error', 'message': 'No nodes provided'}), 400

        # Deploy the contract and return the result
        result = aggregator.deploy_contract()
        if result['status'] == 'success':
            contract_address = result['contractAddress']
            print(f"Contract deployed at address: {contract_address}")

            # Send the contract address to each node
            initialize_nodes(contract_address, node_urls, config)

        return jsonify(result)

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
def init_training():
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
            newAggregatorParams = listen_for_update_agg()
            print("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initialParams = newAggregatorParams

        return jsonify({'status': 'success', 'message': 'Training completed successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def listen_for_update_agg():
    """Listen for the updateAgg event from the blockchain."""
    event_filter = aggregator.deployed_contract.events.updateAggregatorWithParamsFromNodes.create_filter(from_block='latest')

    # Keep polling until the event is detected
    while True:
        try:
            for event in event_filter.get_new_entries():
                print("Received 'updateAgg' event.")
                node_params = event['args']['paramsFromNodes']

                # Aggregate parameters
                newAggregatorParams = aggregator.aggregate_model_params(node_params)

                return newAggregatorParams  # Return updated params after aggregation

        except Exception as e:
            print(f"Error listening for 'updateAgg' event: {str(e)}")

        # Avoid excessive polling
        time.sleep(2)


if __name__ == '__main__':
    # Run the Flask server
    app.run(host='0.0.0.0', port=8080)
