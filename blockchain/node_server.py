from flask import Flask, request, jsonify
from node import Node
import numpy as np
import threading
import time
from web3 import Web3
import os

app = Flask(__name__)

# Configuration
PROVIDER_URL = os.getenv('PROVIDER_URL', 'https://optimism-sepolia.infura.io/v3/524787abec0740b9a443cb825966c31e')
PRIVATE_KEY = os.getenv('PRIVATE_KEY', 'f155acda1fc73fa6f50456545e3487b78fd517411708ffa1f67358c1d3d54977')

# Initialize the Node instance 
node_instance = None

'''
/set-contract-address [POST]
    - Sets up connection with provider
    - Gets config file and intializes node instance
    - Starts 2 threads listening for start training and for update node
'''


@app.route('/init-node', methods=['POST'])
def init_node():
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
        node_instance = Node(contract_address, PROVIDER_URL, PRIVATE_KEY, config, "replica1")

        # Start event listener for start round
        threading.Thread(target=listen_for_start_round).start()

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



def listen_for_start_round():
    """Listen for the 'newRound' event from the blockchain."""
    print("Listening for 'newRound' events...")

    # Generate the event signature for the 'newRound' event
    event_signature = "0x" + Web3.keccak(text="newRound(uint256,string)").hex()
    
    # Get the latest block to start listening from
    latest_block = node_instance.w3.eth.block_number

    while True:
        try:
            # Fetch new logs for the `newRound` event
            logs = node_instance.w3.eth.get_logs({
                'fromBlock': latest_block + 1,  # Start from the latest processed block
                'toBlock': 'latest',
                'address': node_instance.contract_address,
                'topics': [event_signature]  # Filter for the `newRound` event signature
            })

            for log in logs:
                # Decode log data for the `newRound` event
                decoded_event = node_instance.contract_instance.events.newRound().process_log(log)
                init_params = decoded_event['args']['initParams']
                round_number = decoded_event['args']['roundNumber']

                print(f"Received 'newRound' event with initParams: {init_params}, roundNumber: {round_number}")

                # Train model parameters updated from aggregator with local node data
                model_update = node_instance.train_model_params(init_params)
                print(f"Model update: {model_update}")

                # Add node parameters to the blockchain
                result = node_instance.add_node_params(round_number, model_update)
                print(f"add_node_params result: {result}")

            # Update the latest processed block to avoid reprocessing
            if logs:
                latest_block = logs[-1]['blockNumber']

        except Exception as e:
            print(f"Error listening for 'newRound' event: {str(e)}")

        # Sleep to avoid excessive polling
        time.sleep(2)  # Poll every 2 seconds




if __name__ == '__main__':
    # Run the Flask server
    app.run(host='0.0.0.0', port=8081)  # <- needs to be configurable
