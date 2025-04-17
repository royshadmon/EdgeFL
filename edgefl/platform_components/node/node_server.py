"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""

# from dotenv import load_dotenv
from platform_components.EdgeLake_functions.blockchain_EL_functions import get_local_ip
from platform_components.node.node import Node
import numpy as np
import logging
import threading
import time
from dotenv import load_dotenv
import os
import argparse
import requests
import warnings

from uvicorn import run
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from platform_components.lib.logger.logger_config import configure_logging


warnings.filterwarnings("ignore")

app = FastAPI()
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Excludes WARNING, ERROR, CRITICAL

# Initialize the Node instance
node_instance = None
listener_thread = None
stop_listening_thread = False


edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'

class InitNodeRequest(BaseModel):
    replica_name: str
    replica_ip: str
    replica_port: str


@app.post('/init-node')
def init_node(request: InitNodeRequest):
    """Receive the contract address from the aggregator server."""
    global node_instance, listener_thread, stop_listening_thread
    try:
        ip = get_local_ip()

        port = request.replica_port

        replica_name = request.replica_name

        # logger.debug(f"Replica name " + replica_name)

        if listener_thread and listener_thread.is_alive():
            stop_listening_thread = True
            listener_thread.join(timeout=1)

        # Reset the stop flag
        stop_listening_thread = False

        # Instantiate the Node class
        logger.info(f"{replica_name} before initialized")
        node_instance = Node(replica_name, ip, port)
        configure_logging(f"node_server_{port}")
        node_instance.currentRound = 1

        logger.info(f"{replica_name} successfully initialized")

        # Start event listener for start round
        listener_thread = threading.Thread(
            target=listen_for_start_round,
            args=(node_instance, lambda: stop_listening_thread)
        )
        listener_thread.daemon = True  # Make thread daemon so it exits when main thread exits
        listener_thread.start()

        return {
            'status': 'success',
            'message': 'Contract address set and Node initialized successfully'
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

'''
/receive_data [POST] (data)
    - Endpoint to receive data block from the simulated data stream
'''
class ReceiveDataRequest(BaseModel):
    data: list

# @app.route('/receive_data', methods=['POST'])
@app.post('/receive_data')
def receive_data(request: ReceiveDataRequest):
    if not node_instance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Node instance not initialized"
        )
    if request.data:
        node_instance.add_data_batch(np.array(request.data))
        return {
            "status": "data_received",
            "batch_size": len(request.data)
        }
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No Data Provided"
    )

def listen_for_start_round(nodeInstance, stop_event):
    logger.debug(f"listening for start round {nodeInstance.currentRound}")
    while True:
        try:
            # next_round = nodeInstance.currentRound + 1

            # logger.debug(f"listening for start round {nodeInstance.currentRound}")

            headers = {
                'User-Agent': 'AnyLog/1.23',
                'command': f'blockchain get r{nodeInstance.currentRound}'
            }
            response = requests.get(edgelake_node_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                # logger.debug(f"Response Data: {data}")  # Debugging line

                round_data = None
                for item in data:
                    # Check if the key exists in the current dictionary
                    if f'r{nodeInstance.currentRound}' in item:
                        round_data = item[f'r{nodeInstance.currentRound}']
                        break  # Stop searching once the current round's data is found

                if round_data:
                    logger.debug(f"Round Data: {round_data}")  # Debugging line
                    paramsLink = round_data.get('initParams', '')
                    ip_port = round_data.get('ip_port', '')
                    modelUpdate_metadata = nodeInstance.train_model_params(paramsLink, nodeInstance.currentRound, ip_port)
                    nodeInstance.add_node_params(nodeInstance.currentRound, modelUpdate_metadata)
                    logger.info(f"[Round {nodeInstance.currentRound}] Step 3 Complete: Model parameters published")
                    nodeInstance.currentRound += 1
                # else: # Debugging line
                #     logger.error(f"No data found for round r{nodeInstance.currentRound}")

            time.sleep(5)  # Poll every 2 seconds
        except Exception as e:
            logger.error(f"Error in listener thread: {str(e)}")
            time.sleep(2)

# @app.route('/inference', methods=['POST'])
@app.post('/inference')
def inference():
    """Inference on current model w/ data passed in."""
    try:

        logger.info("received inference request")
        results = node_instance.inference()
        response = {
            'status': 'success',
            'message': 'Inference completed successfully',
            'model_accuracy': str(results),
        }
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

class InferenceRequest(BaseModel):
    input: list[float] = [244.46153846153845, 453, 0, 52.29666666666667, 0.0375170724933045, 20.515]

# @app.route('/infer', methods=['POST'])
@app.post('/infer')
def direct_inference(request: InferenceRequest):
    """Inference on current model w/ data passed in."""
    try:
        float_list = request.input
        if len(float_list) != 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ML model input needs to be of len 6"
            )
        results = node_instance.direct_inference(np.array(float_list))
        response = {
            'prediction': str(results),
        }
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

if __name__ == '__main__':
    global port
    parser = argparse.ArgumentParser(description="Run the Node Server.")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on.")
    args = parser.parse_args()

    run(
    "platform_components.node.node_server:app",
        host="0.0.0.0",
        port=args.port,
        reload=False  # Enable auto-reload on code changes (optional)
    )