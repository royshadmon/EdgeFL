from flask import Flask, request, jsonify
from node import Node
import numpy as np
import threading
import time
import requests
import json

app = Flask(__name__)

# Configuration
# PROVIDER_URL = 'http://127.0.0.1:8545'  # <- ganache test network
# # From my ganache test network. Everytime you run the CLI, you get a new set of accounts and private keys so be sure to
# # change this value.
# PRIVATE_KEY = '0x37bf2e24cc36ca7a752a368da4113c6d73226d73b79dc419dcf8a586c531ed42'

PROVIDER_URL = 'https://optimism-sepolia.infura.io/v3/524787abec0740b9a443cb825966c31e'
PRIVATE_KEY = 'f155acda1fc73fa6f50456545e3487b78fd517411708ffa1f67358c1d3d54977'
PUBLIC_KEY = "0x5F02C14eDd7491e339bDf4e942b228A688515838" # use for node addresses 

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
    node_id = request.json.get('node_id')
    round_number = request.json.get('round')
    if data:
        node_instance.add_data_batch(np.array(data))
        # return jsonify({"status": "data_received", "batch_size": len(data)})
    
        # add to sql table
        add_data_response = requests.post(
            'http://localhost:5000/add_data',
            json={
                "node_id": node_id,
                "round": round_number,
                "batch_data": json.dumps(data['features'])  # assuming `features` is the actual data
            }
        )

        if add_data_response.status_code == 201:
            return jsonify({"status": "success", "message": "Data received and added to database"}), 201
        else:
            return jsonify({"error": "Failed to add data to database", "details": add_data_response.json()}), 500
    
    return jsonify({"error": "No data provided"}), 400


def listen_for_start_round():
    """Listen for the 'newRound' event from the blockchain."""
    print("Listening for 'newRound' events...")

    event_filter = node_instance.contract_instance.events.newRound.create_filter(from_block='latest')

    while True:
        try:
            for event in event_filter.get_new_entries():
                print(f"Received 'startRound' event.")
                init_params = event['args']['initParams']
                round_number = event['args']['roundNumber']

                # Train model parameters updated from aggregator with local node data
                model_update = node_instance.train_model_params(init_params)
                print(model_update)

                # add node params to the block chain
                result = node_instance.add_node_params(round_number, model_update)
                print(f"add_node_params result: {result}")


        except Exception as e:
            print(f"Error listening for 'newRound' event: {str(e)}")

        time.sleep(2)  # Poll every 2 seconds




if __name__ == '__main__':
    # Run the Flask server
    app.run(host='0.0.0.0', port=8081)  # <- needs to be configurable
