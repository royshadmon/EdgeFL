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
import requests

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
listener_thread = None
stop_listening_thread = False


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
    global node_instance, listener_thread, stop_listening_thread
    try:
        # # Get the contract address from the request body
        # contract_address = request.json.get('contractAddress')

        config = request.json.get('config')

        if not config:
            return jsonify({'status': 'error', 'message': 'No config provided'}), 400
        if listener_thread and listener_thread.is_alive():
            stop_listening_thread = True
            listener_thread.join(timeout=1)

        # Reset the stop flag
        stop_listening_thread = False

        # Instantiate the Node class
        node_instance = Node(config, "node1")
        node_instance.currentRound = 1

        print("replica 1 successfully initialized")

        # Start event listener for start round
        listener_thread = threading.Thread(
            target=listen_for_start_round,
            args=(node_instance, lambda: stop_listening_thread)
        )
        listener_thread.daemon = True  # Make thread daemon so it exits when main thread exits
        listener_thread.start()

        
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



def listen_for_start_round(node_instance, stop_event):    
    while True:
        try:
            external_ip = os.getenv("EXTERNAL_IP")
            url = f'{external_ip}:32049'
            # next_round = node_instance.currentRound + 1  

            print(f"listening for start round {node_instance.currentRound}") 
            
            headers = {
                'User-Agent': 'AnyLog/1.23',
                'command': f'blockchain get r{node_instance.currentRound}'
            }
            response = requests.get(f'http://{url}', headers=headers)
       
            if response.status_code == 200:
                data = response.json()
                if data:
                    for item in data:
                        round_data = item[f'r{node_instance.currentRound}']
                        if round_data and round_data.get('node') == node_instance.replicaName:
                            paramsLink = round_data.get('initParams', '')
                            modelUpdate = node_instance.train_model_params(paramsLink, node_instance.currentRound)
                            node_instance.add_node_params(node_instance.currentRound, modelUpdate)
                            node_instance.currentRound += 1
                            break
                    
            time.sleep(2)  # Poll every 2 seconds
            
        except Exception as e:
            print(f"Error in listener thread: {str(e)}")
            time.sleep(2)




if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Start the Flask server.')
    parser.add_argument('--port', type=int, default=8081, help='Port to run the Flask server on.')
    args = parser.parse_args()

    # Run the Flask server on the specified port
    app.run(host='0.0.0.0', port=args.port)


