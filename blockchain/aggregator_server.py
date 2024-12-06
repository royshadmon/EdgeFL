import argparse
from dotenv import load_dotenv
import asyncio
from flask import Flask, jsonify, request
from aggregator import Aggregator
import threading
import time
import requests
import os

import torch

import firebase_admin
from firebase_admin import credentials, db

import base64

from ibmfl.model.pytorch_fl_model import PytorchFLModel

app = Flask(__name__)
load_dotenv()

# Use environment variables for sensitive data
PROVIDER_URL = os.getenv('PROVIDER_URL')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

# Initialize the Aggregator instance
aggregator = Aggregator(PROVIDER_URL, PRIVATE_KEY)

'''
CURL REQUEST FOR DEPLOYING CONTRACT-- custom dataset and model, 1 node 

curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081"
  ],
  "model_path": "C:\\Users\\nehab\\cse115d\\testmodel.py",
  "model_init_params": { "module__input_dim": 14 },
  "model_name": "custom_test",
  "model_weights_path": "C:\\Users\\nehab\\cse115d\\model_weights.pt",
  "data_handler_path": "C:\\Users\\nehab\\cse115d_anylog_edgelake\\custom_data_handler.py",
  "data_config": {"data": ["C:\\Users\\nehab\\cse115d_anylog_edgelake\\heart_data\\party_data\\party_0.csv"]}

}'
'''

'''
CURL REQUEST FOR DEPLOYING CONTRACT-- custom dataset and model, 2 nodes

curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081",
    "http://localhost:8082"
  ],
  "model_path": "C:\\Users\\nehab\\cse115d\\testmodel.py",
  "model_init_params": { "module__input_dim": 14 },
  "model_name": "custom_test",
  "model_weights_path": "C:\\Users\\nehab\\cse115d\\model_weights.pt",
  "data_handler_path": "C:\\Users\\nehab\\cse115d_anylog_edgelake\\custom_data_handler.py",
  "data_config": {"data": ["C:\\Users\\nehab\\cse115d_anylog_edgelake\\heart_data\\party_data\\party_0.csv",
                           "C:\\Users\\nehab\\cse115d_anylog_edgelake\\heart_data\\party_data\\party_1.csv"]}
}'
'''

# '''
# CURL REQUEST FOR DEPLOYING CONTRACT-- mnist built in dataset and model, 2 nodes

# curl -X POST http://localhost:8080/init \
# -H "Content-Type: application/json" \
# -d '{
#   "nodeUrls": [
#     "http://localhost:8081",
#     "http://localhost:8082"
#   ],
#   "model_path": "C:\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\federated-learning-lib-main\\examples\\iter_avg\\model_pytorch.py",
#   "model_name": "mnist_test",
#   "model_weights_path": "C:\\Users\\nehab\\cse115d\\model_weights.pt",
#   "data_handler_path": "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\venv38\\Lib\\site-packages\\ibmfl\\util\\data_handlers\\mnist_pytorch_data_handler.py",
#   "data_config": {"npz_file": ["C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\data\\mnist\\data_party0.npz",
#                            "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\data\\mnist\\data_party1.npz"]}
# }'
# '''

'''
curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081",
    "http://localhost:8082"
  ],
  "model_path": "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\federated-learning-lib-main\\examples\\iter_avg\\model_pytorch.py",
  "model_name": "mnist_test",
  "model_weights_path": "C:\\Users\\nehab\\cse115d\\model_weights.pt",
  "data_handler_path": "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\venv38\\Lib\\site-packages\\ibmfl\\util\\data_handlers\\mnist_pytorch_data_handler.py",
  "data_config": {
    "npz_file": [
      "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\data\\mnist\\data_party0.npz",
      "C:\\Users\\nehab\\cse115d\\Anylog-Edgelake-CSE115D\\blockchain\\data\\mnist\\data_party1.npz"
    ]
  }
}'
'''

@app.route('/init', methods=['POST'])
def deploy_contract():
    """Deploy the smart contract with predefined nodes."""
    try:
        data = request.json
        node_urls = data.get('nodeUrls', [])

        model_path = data.get('model_path', os.getenv('MODEL_PYTHON'))
        model_init_params = data.get('model_init_params', None)
        model_name = data.get('model_name', 'model')
        model_weights_path = data.get('model_weights_path')

        # upload model to firebase
        firebase_model_path = f"/models/{model_name}" 
        pytorch_upload(model_path, model_init_params, model_name, firebase_model_path, model_weights_path)

        
        data_handler_path = data.get('data_handler_path')
        data_config = data.get('data_config')

        # upload datahandler to firebase
        firebase_datahandler_path = f"/datahandlers/datahandler"
        datahandler_upload(data_handler_path, data_config, firebase_datahandler_path)

        # Initialize the nodes and send the contract address
        initialize_nodes(firebase_model_path, firebase_datahandler_path, node_urls)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    return f"Initialized nodes with model definition: {model_path}", 200

# creates and uploads a model to firebase for the nodes to download
def pytorch_upload(model_file_path, model_init_params, model_name, firebase_model_path, model_weights_path):
    
    # Read the model class source code
    with open(model_file_path, "r") as f:
        model_source_code = f.read()

    # Dynamically load the model class
    namespace = {}
    exec(model_source_code, namespace)

    # Identify the model class dynamically-- this searches for all classes that are a subset of nn.Module
    model_class = None
    for obj_name, obj in namespace.items():
        if isinstance(obj, type) and issubclass(obj, torch.nn.Module) and obj != torch.nn.Module:
            model_class = obj
            break

    if model_class is None:
        print("No PyTorch model class found in the specified file.")

        print("Searching for nn.Sequential object...")

        # set up fields necessary for get_model_config
        
        # temporary folder for model serialization
        folder_configs = os.path.join(os.getcwd(), "model");
        model_weights_path = os.path.join(folder_configs, "pytorch_sequence.pt");
        dataset = None; # this isn't even used in the model so let's skip for now
        is_agg = False; # this is being uploaded for nodes to use, we want an actual model
        party_id = None; # also isn't even used

        get_model_config = namespace['get_model_config']
        model_config = get_model_config(folder_configs, dataset, is_agg, party_id)

        if model_config is None or "spec" not in model_config:
            raise ValueError("Failed to retrieve a valid model configuration.")
        
        #print("Model Config: ", model_config)

        # build model_specs
        model_specs = model_config['spec']
        print("model specs: ", model_specs)

        # Initialize PytorchFLModel
        fl_model = PytorchFLModel(
            model_name="Pytorch_NN",
            model_spec=model_specs
        )
        

    else:
        print("Identified model class:", model_class)

        # Initialize PytorchFLModel
        fl_model = PytorchFLModel(
            model_name="Pytorch_NN",
            pytorch_module=model_class,
            module_init_params=model_init_params,
        )

        # Save model weights
        model_weights_path = os.path.join(os.getcwd(), "model\\pytorch_sequence.pt");
        fl_model.save_model(filename=model_weights_path)

        model_specs = None


    # Encode the source code and model weights
    encoded_source_code = encode_to_base64(model_source_code)
    with open(model_weights_path, "rb") as f:
        encoded_weights = encode_to_base64(f.read())

    # define model info to upload
    model_data = {
        "source_code": encoded_source_code,
        "weights": encoded_weights,
        "init_params": model_init_params,
        "model_spec": model_specs
    }

    firebase_model_ref = db.reference(firebase_model_path)
    firebase_model_ref.set(model_data)
    print(f"PytorchFLModel uploaded to Firebase Realtime Database at {firebase_model_path}.")

# creates and uploads a datahandler for nodes to download
def datahandler_upload(datahandler_file_path, data_config, firebase_datahandler_path):

    # read source code
    with open(datahandler_file_path, "r") as f:
        datahandler_source_code = f.read()
    
    # Encode the source code and configuration
    encoded_source_code = encode_to_base64(datahandler_source_code)
    encoded_data_config = encode_to_base64(str(data_config))

    # Prepare the data to upload
    datahandler_data = {
        "source_code": encoded_source_code,
        "data_config": encoded_data_config,
    }

    # upload to firebase
    datahandler_firebase_ref = db.reference(firebase_datahandler_path)
    datahandler_firebase_ref.set(datahandler_data)
    print(f"DataHandler uploaded to Firebase Realtime Database at {firebase_datahandler_path}")


def encode_to_base64(data):
    """Encode binary or text data to Base64."""
    if isinstance(data, bytes):
        return base64.b64encode(data).decode("utf-8")
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")

def decode_from_base64(data):
    """Decode Base64 data to binary or text."""
    return base64.b64decode(data)


def initialize_nodes(firebase_model_path, firebase_datahandler_path, node_urls):
    """Send the deployed contract address to multiple node servers."""
    for urlCount in range(len(node_urls)):
        try:
            url = node_urls[urlCount]
            print(f"Sending contract address to node at {url}")

            response = requests.post(f'{url}/init-node', json={
                'replica_name': f"node{urlCount}",
                'firebase_model_path': firebase_model_path,
                'firebase_datahandler_path': firebase_datahandler_path
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
    print('entered start_training endpoint')
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
            print("Finished start_round function")
            # Listen for updates from nodes
            newAggregatorParams = await listen_for_update_agg(min_params, r)
            print("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initialParams = newAggregatorParams

        return jsonify({'status': 'success', 'message': 'Training completed successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


async def listen_for_update_agg(min_params, roundNumber):
    """Asynchronously poll for aggregated parameters from the blockchain."""
    print("Aggregator listening for updates...")
    url = f'http://{os.getenv("EXTERNAL_IP")}:32049'

    while True:
        try:
            # Check parameter count for node responses
            count_response = requests.get(url, headers={
                'User-Agent': 'AnyLog/1.23',
                "command": f"blockchain get r{roundNumber} count"
            })

            if count_response.status_code == 200:
                count_data = count_response.json()
                count = len(count_data) if isinstance(count_data, list) else int(count_data)

                # If enough parameters, get the URL
                if count >= min_params:
                    params_response = requests.get(url, headers={
                        'User-Agent': 'AnyLog/1.23',
                        "command": f"blockchain get r{roundNumber}"
                    })

                    if params_response.status_code == 200:
                        result = params_response.json()
                        # print(f"blockchain get r{roundNumber} returns {result}")

                        if result and len(result) > 0:
                            # Extract all trained_params into a list
                            node_params_links = [
                                item[f'r{roundNumber}']['trained_params']
                                for item in result
                                if f'r{roundNumber}' in item
                            ]

                            print(f"Collected trained_params links: {node_params_links}")  # Debugging line

                            # Aggregate the parameters
                            aggregated_params_link = aggregator.aggregate_model_params(
                                node_param_download_links=node_params_links
                            )
                            return aggregated_params_link

        except Exception as e:
            print(f"Error in aggregator listener: {e}")

        await asyncio.sleep(2)

# added inference endpoint
@app.route('/inference', methods=['POST'])
def inference():
    """Inference on current model w/ data passed in."""
    try:
        data = request.json
        test_data = data.get('data', {})

        results = aggregator.inference(aggregator.fusion_model.fl_model, test_data)

        response = {
            'status': 'success',
            'message': 'Inference completed successfully',
            'model_accuracy': results['acc'] * 100,
            'classification_report': results['classificatio_report']
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    # Add argument parsing to make the port configurable
    parser = argparse.ArgumentParser(description="Run the Aggregator Server.")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on")
    args = parser.parse_args()

    # Run the Flask server on the provided port
    app.run(host='0.0.0.0', port=args.port)
