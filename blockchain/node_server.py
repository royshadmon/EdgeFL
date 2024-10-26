from flask import Flask
from node import Node
import threading
import time

app = Flask(__name__)

# Configuration
PROVIDER_URL = 'http://127.0.0.1:8545' # <- might need to change this 
PRIVATE_KEY = '<NODE-PRIVATE-KEY>' # <- need to change this for each nodes private key 
CONTRACT_ADDRESS = None

# Initialize the Node instance 
node_instance = None

@app.route('/set-contract-address', methods=['POST'])
def set_contract_address():
    """Receive the contract address from the aggregator server."""
    global CONTRACT_ADDRESS, node_instance
    try:
        # Get the contract address from the request body
        CONTRACT_ADDRESS = request.json.get('contractAddress')

        if not CONTRACT_ADDRESS:
            return jsonify({'status': 'error', 'message': 'No contract address provided'}), 400

        print(f"Received contract address: {CONTRACT_ADDRESS}")

        # Instantiate the Node class
        node_instance = Node(CONTRACT_ADDRESS, PROVIDER_URL, PRIVATE_KEY)

        # Start event listeners in separate threads
        threading.Thread(target=listen_for_start_training).start()
        threading.Thread(target=listen_for_update_node).start()

        return jsonify({'status': 'success', 'message': 'Contract address set and Node initialized successfully'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def listen_for_update_node():
    """Listen for the 'updateNode' event from the blockchain."""
    print("Listening for 'updateNode' events...")

    event_filter = node_instance.contract_instance.events.updateNode.createFilter(fromBlock='latest')

    while True:
        try:
            for event in event_filter.get_new_entries():
                updated_params = event['args']['updatedParams']
                print(f"Received 'updateNode' event with updatedParams: {updated_params}")
                # Call add_node_params with the updated parameters
                result = node_instance.add_node_params(updated_params)
                print(f"add_node_params result: {result}")
        except Exception as e:
            print(f"Error listening for 'updateNode' event: {str(e)}")

        time.sleep(2)  # Poll every 2 seconds


def listen_for_start_training():
    """Listen for the 'startTraining' event from the blockchain."""
    print("Listening for 'startTraining' events...")

    event_filter = node_instance.contract_instance.events.startTraining.createFilter(fromBlock='latest')

    while True:
        try:
            for event in event_filter.get_new_entries():
                print("Received 'startTraining' event.")
                # Call add_node_params with an empty list
                result = node_instance.add_node_params([])
                print(f"add_node_params result: {result}")
        except Exception as e:
            print(f"Error listening for 'startTraining' event: {str(e)}")

        time.sleep(2)  # Poll every 2 seconds



if __name__ == '__main__':
    # Run the Flask server
    app.run(host='0.0.0.0', port=5001) # <- this needs to be configurable
