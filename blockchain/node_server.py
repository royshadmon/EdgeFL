from flask import Flask, request, jsonify
from node import Node
import numpy as np
import threading
import time

app = Flask(__name__)

# Configuration
PROVIDER_URL = 'http://127.0.0.1:8545'  # <- ganache test network
# From my ganache test network. Everytime you run the CLI, you get a new set of accounts and private keys so be sure to
# change this value. Should be different than aggregators private key
PRIVATE_KEY = '0x0e7a408d373289dc8ca6e92c01ae6e2493f8d9db153ce4bc1e8c0fc0701b24b5'

# Initialize the Node instance 
node_instance = None

'''
/set-contract-address [POST]
    - Sets up connection with provider
    - Gets config file and intializes node instance
    - Starts 2 threads listening for start training and for update node
'''


@app.route('/set-contract-address', methods=['POST'])
def set_contract_address():
    """Receive the contract address from the aggregator server."""
    global node_instance
    try:
        # Get the contract address from the request body
        contract_address = request.json.get('contractAddress')

        if not contract_address:
            return jsonify({'status': 'error', 'message': 'No contract address provided'}), 400

        print(f"Received contract address: {contract_address}")

        config = request.json.get('config')

        if not config:
            return jsonify({'status': 'error', 'message': 'No config provided'}), 400

        # Instantiate the Node class
        node_instance = Node(contract_address, PROVIDER_URL, PRIVATE_KEY, config)

        # Start event listeners in separate threads
        threading.Thread(target=listen_for_start_training).start()
        threading.Thread(target=listen_for_update_node).start()

        return jsonify({'status': 'success', 'message': 'Contract address set and Node initialized successfully'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


'''
/receive_data [POST] (data)
    - Endpoint to receive data block from the simulated data stream
'''


@app.route('/receive_data', methods=['POST'])
def receive_data():
    data = request.json.get('data')
    if data:
        node_instance.add_data_batch(np.array(data))
        return jsonify({"status": "data_received", "batch_size": len(data)})
    return jsonify({"error": "No data provided"}), 400


def listen_for_update_node():
    """Listen for the 'updateNode' event from the blockchain."""
    print("Listening for 'updateNode' events...")

    event_filter = node_instance.contract_instance.events.updateNode.create_filter(from_block='latest')

    while True:
        try:
            for event in event_filter.get_new_entries():
                print(f"Received 'updateNode' event.")
                aggregator_params = event['args']['aggregatorParams']

                # Train model parameters updated from aggregator with local node data
                response = node_instance.train_model_params(aggregator_params)
                print(response)

                # Call add_node_params with the updated parameters
                result = node_instance.add_node_params()
                print(f"add_node_params result (i.e. nodes model parameters): {result}")
        except Exception as e:
            print(f"Error listening for 'updateNode' event: {str(e)}")

        time.sleep(2)  # Poll every 2 seconds


def listen_for_start_training():
    """Listen for the 'startTraining' event from the blockchain."""
    print("Listening for 'startTraining' events...")

    event_filter = node_instance.contract_instance.events.startTraining.create_filter(from_block='latest')

    while True:
        try:
            for event in event_filter.get_new_entries():
                print("Received 'startTraining' event.")
                # Call add_node_params with an empty list
                result = node_instance.train_model_params("some value for starting parameters")
                print(f"start_training result (i.e. nodes model parameters after training): {result}")
        except Exception as e:
            print(f"Error listening for 'startTraining' event: {str(e)}")

        time.sleep(2)  # Poll every 2 seconds


if __name__ == '__main__':
    # Run the Flask server
    app.run(host='0.0.0.0', port=8081)  # <- needs to be configurable
