"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""


import argparse
from dotenv import load_dotenv
import asyncio
from platform_components.aggregator.aggregator import Aggregator
import logging
import requests
import os

import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from platform_components.EdgeLake_functions.blockchain_EL_functions import get_local_ip
import warnings

from platform_components.lib.logger.logger_config import configure_logging


warnings.filterwarnings("ignore")

app = FastAPI()
load_dotenv()

configure_logging("aggregator_server")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Excludes WARNING, ERROR, CRITICAL

# Initialize the Aggregator instance
ip = get_local_ip()
port = os.getenv("SERVER_PORT", "8080")
aggregator = Aggregator(ip, port)


#######  FASTAPI IMPLEMENTATION  #######

class InitRequest(BaseModel):
    nodeUrls: list[str]
    index: str

class TrainingRequest(BaseModel):
    totalRounds: int
    minParams: int

class ContinueTrainingRequest(BaseModel):
    additionalRounds: int
    minParams: int

# @app.route('/init', methods=['POST'])

@app.post("/init")
def init(request: InitRequest):
    """Deploy the smart contract with predefined nodes."""
    try:
        # Initialize the nodes on specified index and send the contract address
        node_urls, index = request.nodeUrls, request.index
        aggregator.index = index

        aggregator.initialize_file_write_paths(index) # this is done here; check why in aggregator.py
        initialize_nodes(node_urls, index)
        aggregator.initialize_index_on_blockchain(index)
        logger.info(f"Initialized nodes with index ({index}): {request.nodeUrls}")
        return {
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to initialize nodes with index ({index}): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def initialize_nodes(node_urls: list[str], index):
    """Send the deployed contract address to multiple node servers."""
    if index not in aggregator.node_count:
        aggregator.node_count[index] = 0

    if index not in aggregator.node_urls:
        aggregator.node_urls[index] = set()

    for urlCount, url in enumerate(node_urls):
        try:
            my_url = node_urls[urlCount].split('/')[-1]
            my_url = my_url.split(':')
            logger.info(f"Initializing model at {url}")

            if url in aggregator.node_urls[index]: # don't initialize for an existing node url
                logger.info(f"Model at {url} already exists for index {index}.")
                continue

            response = requests.post(f'{url}/init-node', json={
                'replica_ip': my_url[0],
                'replica_port': my_url[1],
                'replica_name': f"node{aggregator.node_count[index] + 1}",
                'replica_index': index
            })

            if response.status_code == 200:
                aggregator.node_count[index] += 1
                aggregator.node_urls[index].add(url)
                logger.info(f"Node at {url} initialized successfully.")
            else:
                logger.error(
                    f"Failed to initialize node at {url}. HTTP Status: {response.status_code}. Response: {response.text}")

        except Exception as e:
            logger.critical(f"Error initializing node: {str(e)}")


@app.post('/start-training')
async def init_training(request: TrainingRequest):
    """Start the training process by setting the number of rounds."""
    try:
        index = aggregator.index
        node_count = aggregator.node_count[index]
        additional_params_added = 0 # accounts for nodes added during training

        num_rounds = request.totalRounds
        min_params = request.minParams
        if min_params > node_count: # prevents stalling when minParams > # of active nodes; warns user
            logger.info(
                f"minParams ({min_params}) is greater than number of active nodes ({node_count}). Using active nodes as minParams."
            )
            min_params = node_count

        if num_rounds <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of rounds must be positive"
            )

        logger.info(f"{num_rounds} {'round' if num_rounds == 1 else 'rounds'} of training started.")

        initial_params = ''

        for r in range(1, num_rounds + 1):
            logger.info(f"Starting training round {r}")
            aggregator.start_round(initial_params, r, index)
            logger.debug("Sent initial parameters to nodes")

            # Listen for updates from nodes
            new_node_count = aggregator.node_count[index]
            if new_node_count > node_count: # detects newly added nodes
                additional_params_added += (new_node_count - node_count)
                node_count = new_node_count
            new_aggregator_params = await listen_for_update_agg(min_params + additional_params_added, r, index)
            logger.debug("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initial_params = new_aggregator_params
            logger.info(f"[Round {r}] Step 4 Complete: model parameters aggregated")

            # Track the last agg model file because it's not stored in a policy after the last round
            aggregator.store_most_recent_agg_params(initial_params, index)


        return {
            "status": "success",
            "message": "Training completed successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

        
async def listen_for_update_agg(min_params, roundNumber, index):
    """Asynchronously poll for aggregated parameters from the blockchain."""
    logger.info("listening for updates...")
    url = f'http://{os.getenv("EXTERNAL_IP")}'

    while True:
        try:
            # Check parameter count
            count_response = requests.get(url, headers={
                'User-Agent': 'AnyLog/1.23',
                "command": f"blockchain get {index}-a{roundNumber} count"
            })

            if count_response.status_code == 200:
                count_data = count_response.json()
                count = len(count_data) if isinstance(count_data, list) else int(count_data)

                # If enough parameters, get the URL
                if count >= min_params:
                    params_response = requests.get(url, headers={
                        'User-Agent': 'AnyLog/1.23',
                        "command": f"blockchain get {index}-a{roundNumber}"
                    })

                    if params_response.status_code == 200:
                        result = params_response.json()
                        if result and len(result) > 0:
                            # Extract all trained_params into a list

                            node_params_links = [
                                item[f'{index}-a{roundNumber}']['trained_params_local_path']
                                for item in result
                                if f'{index}-a{roundNumber}' in item
                            ]

                            ip_ports = [
                                item[f'{index}-a{roundNumber}']['ip_port']
                                for item in result
                                if f'{index}-a{roundNumber}' in item
                            ]

                            # Aggregate the parameters
                            aggregated_params_link = aggregator.aggregate_model_params(
                                node_param_download_links=node_params_links,
                                ip_ports=ip_ports,
                                round_number=roundNumber,
                                index=index
                            )
                            return aggregated_params_link

        except Exception as e:
            logger.error(f"Aggregator_server.py --> Waiting for file: {e}")

        await asyncio.sleep(2)


@app.post('/continue-training')
async def continue_training(request: ContinueTrainingRequest):
    """Continue training from the last completed round."""
    try:
        index = aggregator.index
        node_count = aggregator.node_count[index]
        additional_params_added = 0 # accounts for nodes added during training

        additional_rounds = request.additionalRounds
        min_params = request.minParams
        if min_params > node_count: # prevents stalling when minParams > # of active nodes; warns user
            logger.info(
                f"minParams ({min_params}) is greater than number of active nodes ({node_count}). Using active nodes as minParams."
            )
            min_params = node_count

        if additional_rounds <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid number of additional rounds"
            )

        # Get the last round number from the blockchain layer
        last_round = get_last_round_number()
        if last_round is None:
            raise HTTPException(
                status_code=400,
                detail="No previous training found"
            )
        logger.info(f"Continuing training from round {last_round}, adding {additional_rounds} more rounds.")

        # Fetch the most recent aggregated model parameters
        initial_params = get_last_aggregated_params()
        if not initial_params:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch aggregated parameters from round {last_round}"
            )

        # Continue training for the specified number of additional rounds
        for r in range(last_round + 1, last_round + additional_rounds + 1):
            logger.info(f"Starting training round {r}")
            aggregator.start_round(initial_params, r, index)
            logger.debug("Sent initial parameters to nodes")

            # Listen for updates from nodes
            new_node_count = aggregator.node_count[index]
            if new_node_count > node_count:  # detects newly added nodes
                additional_params_added += (new_node_count - node_count)
                node_count = new_node_count
            new_aggregator_params = await listen_for_update_agg(min_params + additional_params_added, r, index)
            logger.debug("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initial_params = new_aggregator_params
            logger.info(f"[Round {r}] Step 4 Complete: model parameters aggregated")

            # Track the last agg model file because it's not stored in a policy after the last round
            aggregator.store_most_recent_agg_params(initial_params, index)

        return {
            'status': 'success',
            'message': f'Training continued successfully from round {last_round + 1} to {last_round + additional_rounds}'
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


def get_last_round_number():
    """Get the last completed round number from the blockchain."""
    url = f'http://{os.getenv("EXTERNAL_IP")}'

    try:
        # Query the blockchain for all 'r' prefixed keys to find the highest round number
        index = aggregator.index
        response = requests.get(url, headers={
            'User-Agent': 'AnyLog/1.23',
            "command": f"blockchain get * where [index] = {index} and [node_type] = aggregator"
        })

        if response.status_code == 200:
            policies = response.json()
            if not policies or not isinstance(policies, list):
                return None

            # Extract round numbers from keys like '{index}-r1', '{index}-r2', etc.
            highest_round_number = 0
            for policy in policies:
                # if key.startswith('a') and key[1:].isdigit():
                #     round_numbers.append(int(key[1:]))
                key = next(iter(policy)) # it is dict form at first
                if key[-1] == 'r':
                    break

                _, number = key.rsplit("-r", 1)
                highest_round_number = max(highest_round_number, int(number))

            if highest_round_number == 0:
                return None

            return highest_round_number
        else:
            logger.error(f"Error fetching keys: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error fetching last round number: {str(e)}")
        return None


def get_last_aggregated_params():
    """Get the aggregated parameters from the specified round."""
    url = f'http://{os.getenv("EXTERNAL_IP")}'
    try:
        # Get the aggregated parameters from index-r
        index = aggregator.index
        response = requests.get(url, headers={
            'User-Agent': 'AnyLog/1.23',
            "command": f"blockchain get {index}-r"
        })

        if response.status_code == 200:
            result = response.json()
            if result and isinstance(result, list) and len(result) > 0:
                for item in result:
                    if f'{index}-r' in item and 'initParams' in item[f'{index}-r']:
                        return item[f'{index}-r']['initParams']

            logger.info(f"No aggregated parameters found in policy {index}-r")
            return None

        else:
            logger.error(f"Error fetching aggregated parameters: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error fetching aggregated parameters: {str(e)}")
        return None

if __name__ == '__main__':
    # Add argument parsing to make the port configurable
    parser = argparse.ArgumentParser(description="Run the Aggregator Server.")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on.")
    args = parser.parse_args()

    uvicorn.run(
        "aggregator_server:app",
        host="0.0.0.0",
        port=args.port,
        reload=False  # Enable auto-reload on code changes (optional)
    )