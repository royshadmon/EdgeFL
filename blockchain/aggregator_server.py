import argparse
from dotenv import load_dotenv
import asyncio
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
  "contractAddress": "0xE9bdFc2788D52A904a01cC58c611D354c292d42f"
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
            print("Sent initial parameters to nodes")

            # Listen for updates from nodes
            newAggregatorParams = await listen_for_update_agg(min_params, r)
            print("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initialParams = newAggregatorParams

        return jsonify({'status': 'success', 'message': 'Training completed successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# async def listen_for_update_agg(min_params, roundNumber):
#     """Asynchronously poll for the 'updateAggregatorWithParamsFromNodes' event from the blockchain."""
#     print("Aggregator listening for updates...")

#     while True:
#         # Get the URL properly formatted
#         external_ip = os.getenv("EXTERNAL_IP")
#         url = f'{external_ip}:32049'

#         # curl: listen for enough params to be added
#         headers = {
#             'User-Agent': 'AnyLog/1.23',
#             "command": f"blockchain get a{roundNumber} count",
#         }

#         print("Polling for count...")
#         response = requests.get(f'http://{url}', headers=headers)
#         print("got the count response")
#         if response.status_code == 200:
#             try:
#                 count_data = response.json()
#                 print(f"count_data: {count_data}")
#                 if isinstance(count_data, (int, str)):
#                     count = int(count_data)
#                 else:
#                     count = 0
#                 print(f"Current count: {count}")
#             except (ValueError, TypeError) as e:
#                 print(f"Error parsing count response: {e}")
#                 count = 0
#         else:
#             print(f"Failed to get count: {response.text}")
#             count = 0

#         if count >= min_params:
#             headers = {
#                 'User-Agent': 'AnyLog/1.23',
#                 "command": f"blockchain get a{roundNumber}",
#             }

#             response = requests.get(f'http://{url}', headers=headers)
#             if response.status_code == 200:
#                 try:
#                     result_data = response.json()
#                     if result_data and len(result_data) > 0:
#                         # Extract just the URL
#                         trained_params_url = result_data[0][f'a{roundNumber}']['trained_params']
#                         return trained_params_url
#                 except Exception as e:
#                     print(f"Error parsing result data: {e}")
#                     time.sleep(2)
#                     continue
        
#         # Asynchronously sleep to avoid excessive polling
#         time.sleep(2)  # Poll every 2 seconds
async def listen_for_update_agg(min_params, roundNumber):
    """Asynchronously poll for aggregated parameters from the blockchain."""
    print("Aggregator listening for updates...")
    url = f'http://{os.getenv("EXTERNAL_IP")}:32049'

    while True:
        try:
            # Check parameter count
            count_response = requests.get(url, headers={
                'User-Agent': 'AnyLog/1.23',
                "command": f"blockchain get a{roundNumber} count"
            })
            
            if count_response.status_code == 200:
                count_data = count_response.json()
                count = len(count_data) if isinstance(count_data, list) else int(count_data)

                # If enough parameters, get the URL
                if count >= min_params:
                    params_response = requests.get(url, headers={
                        'User-Agent': 'AnyLog/1.23',
                        "command": f"blockchain get a{roundNumber}"
                    })
                    
                    if params_response.status_code == 200:
                        result = params_response.json()
                        if result and len(result) > 0:
                            return result[0][f'a{roundNumber}']['trained_params']

        except Exception as e:
            print(f"Error in aggregator listener: {e}")
        
        await asyncio.sleep(2)
if __name__ == '__main__':
    # Add argument parsing to make the port configurable
    parser = argparse.ArgumentParser(description="Run the Aggregator Server.")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on")
    args = parser.parse_args()

    # Run the Flask server on the provided port
    app.run(host='0.0.0.0', port=args.port)