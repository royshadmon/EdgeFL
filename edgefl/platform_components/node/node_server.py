"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""
from starlette.responses import PlainTextResponse

# from dotenv import load_dotenv
from platform_components.EdgeLake_functions.blockchain_EL_functions import get_local_ip, fetch_data_from_db, \
    connect_to_db, get_all_databases
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
from contextlib import asynccontextmanager
from pydantic import BaseModel

from platform_components.lib.logger.logger_config import configure_logging


warnings.filterwarnings("ignore")

load_dotenv()

# node that system_query resides on
QUERY_NODE_URL=f"htt://{os.getenv('QUERY_NODE_URL')}"
# Edge Node conntaining data
EDGE_NODE_CONN=os.getenv('QUERY_NODE_URL')
# Logical database name
LOGICAL_DATABASE=[os.getenv('LOGICAL_DATABASE')]
# Table containing trained data
TRAIN_TABLE=os.getenv('TRAIN_TABLE')
# Table containing test data
TEST_TABLE=os.getenv('TEST_TABLE')


db_password = os.getenv("PSQL_DB_PASSWORD")
db_host = os.getenv("PSQL_HOST")
db_port = os.getenv("PSQL_PORT")

db_list = os.getenv('LOGICAL_DATABASE').split(',')
edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
edgelake_node_port = edgelake_node_url.split(":")[2]

configure_logging(f"node_server_{edgelake_node_port}")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Excludes WARNING, ERROR, CRITICAL

# Initialize the Node instance
node_instance = None
listener_thread = None
stop_listening_thread = False

def check_data():
    sql_stmt = f'sql {LOGICAL_DATABASE} format=json and stat=false "select count(*) as count from %s"'
    headers = {
        'command': None,
        'User-Agent': 'AnyLog/1.23',
        'destination': EDGE_NODE_CONN 
    }

    for table in [TRAIN_TABLE, TEST_TABLE]:
        headers['command'] = sql_stmt % table
        try:
            response = requests.get(url=QUERY_NODE, headers=headers)
            response.raise_for_status()
            if int(response.json()['Query'][0]['count']) < 1:
                raise ValueError(f"No data found in the database: {LOGICAL_DATABASE}.{table}")
        except Exception as error:
            raise Exception(f"Failed to execute GET for table {LOGICAL_DATABASE}.{table} (Error: {error})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_list
    # logger.info(f"Node server on port {edgelake_node_port} starting up.")

    # Get all connected databases from the EdgeLake node
    db_list = LOGICAL_DATABASE

    yield
    # logger.info("Node server shutting down.")

app = FastAPI(lifespan=lifespan)


class InitNodeRequest(BaseModel):
    replica_name: str
    replica_ip: str
    replica_port: str
    replica_index: str
    round_number: int
    module_name: str
    module_path: str
    LOGICAL_DATABASE: str


@app.post('/init-node')
def init_node(request: InitNodeRequest):
    global node_instance, listener_thread, stop_listening_thread
    try:
        ip = get_local_ip()
        most_recent_round = request.round_number

        port = request.replica_port
        replica_name = request.replica_name
        index = request.replica_index
        module_name = request.module_name
        module_path = request.module_path

        LOGICAL_DATABASE = request.LOGICAL_DATABASE # testing winniio_fl + mnist_fl DBs

        # Connect to DB if it's not in the EdgeLake node
        # if LOGICAL_DATABASE not in db_list:
        #     connect_to_db(edgelake_node_url, LOGICAL_DATABASE, db_user, db_password, db_host, db_port)
        #     db_list.add(LOGICAL_DATABASE)

        # # Fetch and check for existing data
        # query = f"sql {LOGICAL_DATABASE} SELECT * FROM node_{replica_name} LIMIT 1"
        # check_data = fetch_data_from_db(edgelake_node_url, query)
        # if not check_data:
        #     raise ValueError(f"No data found in the database: {LOGICAL_DATABASE}.")

        check_data()
        # Instantiate the Node class
        logger.info(f"{replica_name} before initialized")
        if not node_instance:
            node_instance = Node(replica_name, ip, port, logger)

        if index not in node_instance.databases:
            node_instance.databases[index] = LOGICAL_DATABASE

        node_instance.initialize_specific_node_on_index(index, module_name, module_path)
        node_instance.round_number[index] = most_recent_round # 1 or current round

        logger.info(f"{replica_name} successfully initialized for ({index})")
        # print(f"indexes: {node_instance.indexes}")
        # print(f"module names: {node_instance.module_names}")
        # print(f"module paths: {node_instance.module_paths}")
        # print(f"starting round numbers: {node_instance.round_number}")
        # print(f"training apps: {node_instance.data_handlers}")

        # Start event listener for start round
        listener_thread = threading.Thread(
            name=f"{replica_name}--{index}",
            target=listen_for_start_round,
            args=(node_instance, index, lambda: stop_listening_thread)
        )
        listener_thread.daemon = True  # Make thread daemon so it exits when main thread exits
        listener_thread.start()

        return {
            'status': 'success',
            'message': 'Node initialized successfully'
        }
    except ValueError as e:
        raise ValueError(
            f"No data found in the database: {LOGICAL_DATABASE}"
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"/init-node - {str(e)}"
        )
    except ConnectionError as e:
        raise ConnectionError(
            f"Unable to access the database tables: {str(e)}"
        )

'''
/receive_data [POST] (data)
    - Endpoint to receive data block from the simulated data stream
'''
class ReceiveDataRequest(BaseModel):
    index: str
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
        node_instance.add_data_batch(request.index, np.array(request.data))
        return {
            "status": "data_received",
            "batch_size": len(request.data)
        }
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No Data Provided"
    )

def listen_for_start_round(nodeInstance, index, stop_event):
    current_round = nodeInstance.round_number[index]

    logger.debug(f"[{index}] listening for start round {current_round}")
    while True:
        try:
            headers = {
                'User-Agent': 'AnyLog/1.23',
                'command': f'blockchain get {index}-r{current_round}'
            }
            response = requests.get(QUERY_NODE_URL, headers=headers)

            if response.status_code == 200:
                data = response.json()
                # logger.debug(f"Response Data: {data}")  # Debugging line

                round_data = None
                for item in data:
                    # Check if the key exists in the current dictionary
                    if f'{index}-r{current_round}' in item:
                        round_data = item[f'{index}-r{current_round}']
                        break  # Stop searching once the current round's data is found

                if round_data:
                    logger.debug(f"[{index}] Round Data: {round_data}")  # Debugging line
                    paramsLink = round_data.get('initParams', '')
                    ip_port = round_data.get('ip_port', '')
                    modelUpdate_metadata = nodeInstance.train_model_params(paramsLink, current_round, ip_port, index)
                    nodeInstance.add_node_params(current_round, modelUpdate_metadata, index)
                    logger.info(f"[{index}][Round {current_round}] Step 3 Complete: Model parameters published")
                    current_round += 1

            time.sleep(5)  # Poll every 2 seconds
        except Exception as e:
            logger.error(f"[{index}] Error in listener thread: {str(e)}")
            time.sleep(2)

# TODO: move to a (helper) file (i.e. 'node_helpers.py'?)
# Extracts initParams from the policy 'index-r' at the specified index
def get_most_recent_agg_params(index):
    policy_name = f"{index}-r"
    agg_params = None

    try:
        headers = {
            'User-Agent': 'AnyLog/1.23',
            'command': f'blockchain get {policy_name}'
        }
        response = requests.get(QUERY_NODE_URL, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if data:
                policy = data[0]
                policy_data = policy[policy_name]
                agg_params = policy_data["initParams"]

        return agg_params
    except Exception as e:
        logger.error(f"[{index}] Error in extracting round number: {str(e)}")

# @app.route('/inference', methods=['POST'])
@app.post('/inference/{index}', response_class=PlainTextResponse)
def inference(index):
    """Inference on current model w/ data passed in."""
    try:
        logger.info(f"[{index}] received inference request")
        if not index:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Index must be specified."
            )
        results = node_instance.inference(index)
        response = (f"{{"
                    f"'index': '{index}',"
                    f" 'status': 'success',"
                    f" 'message': 'Inference completed successfully',"
                    f" 'model_accuracy': '{str(results)}'"
                    f"}}\n")
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

class InferenceRequest(BaseModel):
    input: list[float] = [244.46153846153845, 453, 0, 52.29666666666667, 0.0375170724933045, 20.515]

# TODO: add index and reformat response to FastAPI PlainTextResponse
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
    "node_server:app",
        host="0.0.0.0",
        port=args.port,
        reload=False  # Enable auto-reload on code changes (optional)
    )