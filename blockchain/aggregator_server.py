from flask import Flask, jsonify, request
from aggregator import Aggregator
import threading
import time
import requests

app = Flask(__name__)

# Initialize the Aggregator instance
PROVIDER_URL = 'http://127.0.0.1:8545'  # <- ganache test network
# From my ganache test network. Everytime you run the CLI, you get a new set of accounts and private keys so be sure to
# change this value.
PRIVATE_KEY = '0x6e5ac5342bed40e9b1fab14251db21a98a83294f433878be6cfef9f186dd38db'
aggregator = Aggregator(PROVIDER_URL, PRIVATE_KEY)

TOTAL_ROUNDS = 0  # Number of rounds to be initialized from the init_training method
CURRENT_ROUND = 1  # Track the current round

'''

CURL REQUEST FOR DEPLOYING CONTRACT

curl -X POST http://localhost:8080/deploy-contract \
-H "Content-Type: application/json" \
-d '{
  "nodeAddresses": [
    "0x9385dab67f3a7698A14E483E4A3d8373a2095CE0" <- example node address chosen from ganache test network
  ],
  "nodeUrls": [
    "http://localhost:8081" <- example host where other node is running
  ],
  "config": {  
    "model": {
      "path": "/path/to/model" <- Needs to be a model compatible for ibm FL
    },
    "data": {
      "path": "/path/to/data" <- Needs to be a path to data handler
    }
  }
}'

'''


@app.route('/deploy-contract', methods=['POST'])
def deploy_contract():
    """Deploy the smart contract with predefined nodes."""

    try:
        # Get the list of nodes and node URLs from the request body
        data = request.json
        node_addresses = data.get('nodeAddresses', [])
        node_urls = data.get('nodeUrls', [])
        config = data.get('config', {})

        if not node_addresses:
            return jsonify({'status': 'error', 'message': 'No nodes provided'}), 400

        # Deploy the contract and return the result
        result = aggregator.deploy_contract(node_addresses)
        if result['status'] == 'success':
            contract_address = result['contractAddress']
            print(f"Contract deployed and saved: {contract_address}")

            # Send the contract address to each node
            send_contract_address_to_nodes(contract_address, node_urls, config)

        return jsonify(result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def send_contract_address_to_nodes(contract_address, node_urls, config):
    """Send the deployed contract address to multiple node servers."""
    for url in node_urls:
        try:
            response = requests.post(f'{url}/set-contract-address', json={
                'contractAddress': contract_address,
                'config': config
            })
            if response.status_code == 200:
                print(f"Contract address successfully sent to node at {url}")
            else:
                print(f"Failed to send contract address to {url}: {response.text}")
        except Exception as e:
            print(f"Error sending contract address to {url}: {str(e)}")


@app.route('/init-training', methods=['POST'])
def init_training():
    """Initialize the training process by setting the number of rounds."""
    global TOTAL_ROUNDS, CURRENT_ROUND

    try:
        # Get the number of rounds from the request body
        data = request.json
        TOTAL_ROUNDS = data.get('totalRounds', 0)

        if TOTAL_ROUNDS <= 0:
            return jsonify({'status': 'error', 'message': 'Invalid number of rounds'}), 400

        print(f"Training initialized with {TOTAL_ROUNDS} rounds.")

        # Reset the current round to 1
        CURRENT_ROUND = 1

        # Start the event listener in a separate thread
        listener_thread = threading.Thread(target=listen_for_update_agg)
        listener_thread.start()

        aggregator.init_training()

        return jsonify({'status': 'success', 'message': 'Training initialized successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def listen_for_update_agg():
    """Listen for the updateAgg event from the blockchain."""
    global CURRENT_ROUND

    event_filter = aggregator.deployed_contract.events.updateAgg.create_filter(from_block='latest')

    print(f"Listening for updateAgg events... Total Rounds: {TOTAL_ROUNDS}")

    while CURRENT_ROUND <= TOTAL_ROUNDS:
        try:
            for event in event_filter.get_new_entries():
                node_params = event['args']['nodeParams']
                print(f"Received updateAgg event in round {CURRENT_ROUND}: {node_params}")

                # Call the aggregator's logic to aggregate parameters
                new_model_params = aggregator.aggregate_model_params(node_params)

                # Determine if we need to update nodes (only if not the last round)
                update_nodes = CURRENT_ROUND < TOTAL_ROUNDS

                # Call the update_model_parameters function
                result = aggregator.update_model_parameters(new_model_params, update_nodes)
                print(f"Round {CURRENT_ROUND} update result: {result}")

                # Increment the round counter
                CURRENT_ROUND += 1

                if CURRENT_ROUND > TOTAL_ROUNDS:
                    print("Training completed.")
                    return  # Exit the loop when all rounds are completed

        except Exception as e:
            print(f"Error listening for updateAgg event: {str(e)}")

        # Sleep to avoid excessive polling
        time.sleep(2)  # Poll every 2 seconds


if __name__ == '__main__':
    # Run the Flask server
    app.run(host='0.0.0.0', port=8080)  # <- needs to be configurable
