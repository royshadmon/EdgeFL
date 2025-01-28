import argparse
from dotenv import load_dotenv
import asyncio
from flask import Flask, jsonify, request
from platform_components.aggregator.aggregator import Aggregator
import requests
import os

from platform_components.EdgeLake_functions.blockchain_EL_functions import get_local_ip

app = Flask(__name__)
load_dotenv()

# Use environment variables for sensitive data
PROVIDER_URL = os.getenv("PROVIDER_URL")
PRIVATE_KEY =  os.getenv("PRIVATE_KEY")

# Initialize the Aggregator instance
ip = get_local_ip()
port = app.config.get("SERVER_PORT", "8080")
aggregator = Aggregator(PROVIDER_URL, PRIVATE_KEY, ip, port)

'''
CURL REQUEST FOR DEPLOYING CONTRACT

curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081", 
    "http://localhost:8082"
  ],
  "model_def": 1
}'
'''


@app.route('/init', methods=['POST'])
def deploy_contract():
    """Deploy the smart contract with predefined nodes."""
    try:
        data = request.json
        node_urls = data.get('nodeUrls', [])
        model_def = data.get('model_def', 1)

        # Initialize the nodes and send the contract address
        initialize_nodes(model_def, node_urls)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    return f"Initialized nodes with model definition: {model_def}", 200


def initialize_nodes(model_def, node_urls):
    """Send the deployed contract address to multiple node servers."""
    for urlCount in range(len(node_urls)):
        try:
            url = node_urls[urlCount]
            print(f"Sending contract address to node at {url}")

            response = requests.post(f'{url}/init-node', json={
                'replica_name': f"node{urlCount+1}",
                'model_def': model_def
            })

            # TODO: figure out how to handle response
            # I am assuming that the node initialization above will be successful without actually checking

            # if response.status_code == 200:
            #     print(f"Contract address successfully sent to node at {url}")
            # else:
            #     print(f"Failed to send contract address to {url}: {response.text}")

        except Exception as e:
            print(f"Error sending contract address: {str(e)}")


'''
EXAMPLE CURL REQUEST FOR STARTING TRAINING

curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5, 
  "minParams": 2
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
            aggregator.start_round(initialParams, r)
            # print("Sent initial parameters to nodes")
            # Listen for updates from nodes
            newAggregatorParams = await listen_for_update_agg(min_params, r)
            # print("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initialParams = newAggregatorParams

        return jsonify({'status': 'success', 'message': 'Training completed successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/inference', methods=['POST'])
def inference():
    """Inference on current model w/ data passed in."""
    try:

        # hard coding tht test data right now: test_data = (x_test, y_test)
        (_), test_data = aggregator.fusion_model.data_handler.get_data()

        results = aggregator.inference(test_data)
        response = {
            'status': 'success',
            'message': 'Inference completed successfully',
            'model_accuracy': results['acc'] * 100,
            'classification_report': results['classification_report']
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


async def listen_for_update_agg(min_params, roundNumber):
    """Asynchronously poll for aggregated parameters from the blockchain."""
    print("Aggregator listening for updates...")
    url = f'http://{os.getenv("EXTERNAL_IP")}'

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
                            # Extract all trained_params into a list

                            node_params_links = [
                                item[f'a{roundNumber}']['trained_params_local_path']
                                for item in result
                                if f'a{roundNumber}' in item
                            ]

                            ip_ports = [
                                item[f'a{roundNumber}']['ip_port']
                                for item in result
                                if f'a{roundNumber}' in item
                            ]

                            # Aggregate the parameters
                            aggregated_params_link = aggregator.aggregate_model_params(
                                node_param_download_links=node_params_links,
                                ip_ports=ip_ports,
                                round_number=roundNumber
                            )
                            return aggregated_params_link

        except Exception as e:
            print(f"Aggregator_server.py --> Waiting for file: {e}")

        await asyncio.sleep(2)


if __name__ == '__main__':
    # Add argument parsing to make the port configurable
    parser = argparse.ArgumentParser(description="Run the Aggregator Server.")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on")
    args = parser.parse_args()
    app.config["SERVER_PORT"] = args.port
    # Run the Flask server on the provided port
    app.run(host='0.0.0.0', port=args.port)