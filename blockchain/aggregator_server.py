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
PRIVATE_KEY = '0x37bf2e24cc36ca7a752a368da4113c6d73226d73b79dc419dcf8a586c531ed42'
aggregator = Aggregator(PROVIDER_URL, PRIVATE_KEY)

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
  "expectedNumberOfNodes"
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
        expectedNumberOfNodes = len(node_urls)
        config = data.get('config', {})

        if not node_addresses:
            return jsonify({'status': 'error', 'message': 'No nodes provided'}), 400

        # Deploy the contract and return the result
        result = aggregator.deploy_contract()
        if result['status'] == 'success':
            contract_address = result['contractAddress']
            print(f"Contract deployed and saved: {contract_address}")

            # Send the contract address to each node
            initialize_nodes(contract_address, node_urls, expectedNumberOfNodes, config)
        
        return jsonify(result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def initialize_nodes(contract_address, node_urls, expectedNumberOfNodes, config):
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

EXAMPLE CURL REQUEST

curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5
}'

'''


@app.route('/start-training', methods=['POST'])
def init_training():
    """start the training process by setting the number of rounds."""
    try:
        # Get the number of rounds from the request body
        data = request.json
        num_rounds = data.get('totalRounds', 1) # 1 round default value

        if num_rounds <= 0:
            return jsonify({'status': 'error', 'message': 'Invalid number of rounds'}), 400

        print(f"Training initialized with {num_rounds} rounds.")

        initialParams = ''

        for r in range(num_rounds):
            # start a new round
            aggregator.start_round(initialParams, r)

            # list for updates from nodes
            newAggregatorParams = listen_for_update_agg(r)

            # set initial params to newly aggregated params for next round
            initialParams = newAggregatorParams

        return jsonify({'status': 'success', 'message': 'Training completed successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def listen_for_update_agg(roundNumber):
    """Listen for the updateAgg event from the blockchain."""

    event_filter = aggregator.deployed_contract.events.updateAggregatorWithParamsFromNodes.create_filter(from_block='latest')

    # Keep polling until the event is detected
    while True:
        try:
            events = event_filter.get_new_entries()
            if events:
                print("Received 'updateAgg' event.")
                # Process the event data if needed
                for event in events:
                    node_params = event['args']['paramsFromNodes']
                    nodes_participated = event['args']['numberOfParams']
                    if nodes_participated >= 1:  # some arbitrary number of nodes that need to have participated
                        # aggregate parameters
                        newAggregatorParams = aggregator.aggregate_model_params(node_params)

                        # push aggregated params to blockchain
                        aggregator.updateParams(roundNumber, newAggregatorParams)

                        # return the updated aggregator parameters
                        return newAggregatorParams  # Exit the function once the aggregator updates the values

        except Exception as e:
            print(f"Error listening for 'updateAgg' event: {str(e)}")

        # Sleep to avoid excessive polling
        time.sleep(2)  # Poll every 2 seconds


if __name__ == '__main__':
    # Run the Flask server
    app.run(host='0.0.0.0', port=8080)  # <- needs to be configurable
