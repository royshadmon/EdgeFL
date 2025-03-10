"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""


import argparse
from dotenv import load_dotenv
import asyncio
from platform_components.aggregator.aggregator import Aggregator
import requests
import os

import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from platform_components.EdgeLake_functions.blockchain_EL_functions import get_local_ip
import warnings

warnings.filterwarnings("ignore")

app = FastAPI()
load_dotenv()

# Use environment variables for sensitive data
PROVIDER_URL = os.getenv("PROVIDER_URL")
PRIVATE_KEY =  os.getenv("PRIVATE_KEY")

# Initialize the Aggregator instance
ip = get_local_ip()
port = os.getenv("SERVER_PORT", "8080")
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

#######  FASTAPI IMPLEMENTATION  #######

class InitRequest(BaseModel):
    model_def: int
    nodeUrls: list[str]

class TrainingRequest(BaseModel):
    totalRounds: int
    minParams: int

# @app.route('/init', methods=['POST'])

@app.post("/init")
def deploy_contract(request: InitRequest):
    """Deploy the smart contract with predefined nodes."""
    try:
        # Initialize the nodes and send the contract address
        initialize_nodes(request.model_def, request.nodeUrls)
        return {
            "status": "success",
            "message": f"Initialized nodes with model definition: {request.model_def}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

def initialize_nodes(model_def: int , node_urls: list[str]):
    """Send the deployed contract address to multiple node servers."""
    for urlCount in range(len(node_urls)):
        try:
            url = node_urls[urlCount]
            print(f"Initializing model at {url}")

            response = requests.post(f'{url}/init-node', json={
                'replica_name': f"node{urlCount+1}",
                'model_def': model_def
            })

            if response.status_code == 200:
                print(f"Node at {url} initialized successfully.")
            else:
                print(
                    f"Failed to initialize node at {url}. HTTP Status: {response.status_code}. Response: {response.text}")

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


# @app.route('/start-training', methods=['POST'])
@app.post('/start-training')
async def init_training(request: TrainingRequest):
    """Start the training process by setting the number of rounds."""
    try:
        num_rounds = request.totalRounds
        min_params = request.minParams

        if num_rounds <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of rounds must be positive"
            )

        print(f"{num_rounds} rounds of training started.")

        initial_params = ''

        for r in range(1, num_rounds + 1):
            print(f"Starting training round {r}")
            aggregator.start_round(initial_params, r)
            # print("Sent initial parameters to nodes")
            # Listen for updates from nodes
            new_aggregator_params = await listen_for_update_agg(min_params, r)
            # print("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initial_params = new_aggregator_params
            print(f"[Round {r}] Step 4 Complete: model parameters aggregated")
        return {
            "status": "success",
            "message": "Training completed successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# @app.route('/inference', methods=['POST'])
@app.post('/inference')
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
        return response
    except Exception as e:
        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def listen_for_update_agg(min_params: int, roundNumber):
    """Asynchronously poll for aggregated parameters from the blockchain."""
    print("listening for updates...")
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
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on.")
    args = parser.parse_args()

    uvicorn.run(
        "aggregator_server:app",
        host="0.0.0.0",
        port=args.port,
        reload=True  # Enable auto-reload on code changes (optional)
    )