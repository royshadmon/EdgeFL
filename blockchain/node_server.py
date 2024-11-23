import argparse
from dotenv import load_dotenv

from flask import Flask, request, jsonify
from node import Node
import numpy as np
import threading
import time
from web3 import Web3
import os
import argparse
'''
TO START NODE YOU CAN USE "python3 blockchain/node_server.py --port <port number>"
'''

app = Flask(__name__)
load_dotenv()

# Configuration
PROVIDER_URL = os.getenv('PROVIDER_URL')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

# Initialize the Node instance 
node_instance = None

'''
/set-contract-address [POST]
    - Sets up connection with provider
    - Gets config file and intializes node instance
    - Starts 2 threads listening for start training and for update node
'''
'''
SAMPLE CURL REQUEST COMING FROM AGGREGATOR SERVER:

curl -X POST http://localhost:8081/init-node \
-H "Content-Type: application/json" \
-d '{
  "contractAddress": "your_contract_address_here",
  "config": {
    "key1": "value1",
    "key2": "value2"
  }
}'

Note: when the aggregator server is calling this function, it will be with a new contract address field, but if you are 
calling this endpoint from the terminal for testing you don't need to add it 

SAMPLE CURL COMING FROM COMMAND LINE FOR TESTING:
curl -X POST http://localhost:8081/init-node \
-H "Content-Type: application/json" \
-d '{
  "config": {
    "key1": "value1",
    "key2": "value2"
  }
}'


'''

@app.route('/init-node', methods=['POST'])
def init_node():
    """Receive the contract address from the aggregator server."""
    global node_instance
    try:
        # Get the contract address from the request body
        contract_address = request.json.get('contractAddress')

        # print(f"Received contract address: {contract_address}")

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

    # # Generate the event signature for the 'newRound' event
    # event_signature = "0x" + Web3.keccak(text="newRound(uint256,string)").hex()
    
    # # Get the latest block to start listening from
    # latest_block = node_instance.w3.eth.block_number

    while True:
        # curl command to update
        
        # Sleep to avoid excessive polling
        time.sleep(2)  # Poll every 2 seconds




if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Start the Flask server.')
    parser.add_argument('--port', type=int, default=8081, help='Port to run the Flask server on.')
    args = parser.parse_args()

    # Run the Flask server on the specified port
    app.run(host='0.0.0.0', port=args.port)


