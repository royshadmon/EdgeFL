"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""

import os
from asyncio import sleep
import ast

import numpy as np
import requests
import pickle
from dotenv import load_dotenv

from ibmfl.aggregator.fusion.iter_avg_fusion_handler import IterAvgFusionHandler
from ibmfl.model.model_update import ModelUpdate


from platform_components.EdgeLake_functions.mongo_file_store import copy_file_to_container, create_directory_in_container
from platform_components.EdgeLake_functions.blockchain_EL_functions import insert_policy, \
    check_policy_inserted
from platform_components.EdgeLake_functions.mongo_file_store import read_file, write_file, copy_file_from_container

# from custom_data_handler import CustomMnistPytorchDataHandler

CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')

load_dotenv()


class Aggregator:
    def __init__(self, provider_url, private_key, ip, port):
        self.file_write_destination = os.getenv("FILE_WRITE_DESTINATION")
        self.server_ip = ip
        self.server_port = port
        # Initialize Firebase database connection
        self.database_url = os.getenv('DATABASE_URL')


        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        self.edgelake_tcp_node_ip_port = f'{os.getenv("EXTERNAL_TCP_IP_PORT")}'



        if os.getenv("EDGELAKE_DOCKER_RUNNING").lower() == "false":
            self.docker_running = False
        else:
            self.docker_running = True
            self.docker_file_write_destination = os.getenv("DOCKER_FILE_WRITE_DESTINATION")
            self.docker_container_name = os.getenv("EDGELAKE_DOCKER_CONTAINER_NAME")
            create_directory_in_container(self.docker_container_name, self.docker_file_write_destination)
            create_directory_in_container(self.docker_container_name,f"{self.docker_file_write_destination}/aggregator/")

            # Correctly instantiate the Fusion model here (using IterAvg as place holder for now)
        # Define or obtain hyperparameters and protocol handler for the fusion model
        hyperparams = {}  # Replace with actual hyperparameters as required
        protocol_handler = None  # Replace with an appropriate protocol handler instance or object


        # Correctly instantiate the Fusion model with required arguments
        self.fusion_model = IterAvgFusionHandler(hyperparams, protocol_handler, data_handler=None)

    def get_contract_address(self):

        headers = {
            'User-Agent': 'AnyLog/1.23',
            'Content-Type': 'text/plain',
            'command': 'get !contract'
        }

        response = requests.get(self.edgelake_node_url, headers=headers, data="")
        if response.status_code == 200:
            print(f"Contract address: {response.text}")
            return response.text
        else:
            print(f"Failed to retrieve contract, check for active EdgeLake node")
            exit(-1)

    # function to call the start round function from the smart contract
    def start_round(self, initParamsLink, roundNumber):
        try:

            # headers = {
            #     'User-Agent': 'AnyLog/1.23',
            #     'Content-Type': 'text/plain',
            #     'command': 'blockchain insert where policy = !my_policy and local = true and blockchain = optimism'
            # }

            # Format data exactly like the example curl command but with your values
            # NOTE: ask why are we adding the node num from agg
            data = f'''<my_policy = {{"r{roundNumber}" : {{
                                        "initParams": "{initParamsLink}",
                                        "ip_port": "{self.edgelake_tcp_node_ip_port}"                                
                              }} }}>'''
            success = False
            while not success:
                print("Attempting insert")
                response = insert_policy(self.edgelake_node_url, data)
                if response.status_code == 200:
                    success = True
                else:
                    sleep(np.random.randint(5,15))

                    if check_policy_inserted(self.edgelake_node_url, data):
                        success = True

            print(f"Training initialized with {roundNumber} rounds")

            # response = requests.post(self.edgelake_node_url, headers=headers, data=data)
            if success:
                return {
                    'status': 'success',
                    'message': 'initTraining called successfully'
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Request failed with status code: {response.status_code}'
                }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def aggregate_model_params(self, node_param_download_links, ip_ports, round_number):
        # use the node_param_download_links to get all the file
        # in the form of tuples, like ["('blobs_admin', 'node_model_updates', '1-replica-node1.pkl')"]
        # node_ref = db.reference('node_model_updates')

        decoded_params = []
        # Loop through each provided download link to retrieve node parameter objects
        for i, path in enumerate(node_param_download_links):
            try:

                # make sure directory exists
                filename = path.split('/')[-1]
                os.makedirs(os.path.dirname(
                    f"{self.file_write_destination}/aggregator/"),
                            exist_ok=True)


                if self.docker_running:
                    response = read_file(self.edgelake_node_url, path,
                                         f'{self.docker_file_write_destination}/aggregator/{filename}', ip_ports[i])
                    copy_file_from_container(self.docker_container_name,
                                        f'{self.docker_file_write_destination}/aggregator/{filename}',
                                        f'{self.file_write_destination}/aggregator/{filename}')
                else:
                    response = read_file(self.edgelake_node_url, path,
                                     f'{self.file_write_destination}/aggregator/{filename}', ip_ports[i])


                if response.status_code == 200:
                    sleep(1)
                    with open(f'{self.file_write_destination}/aggregator/{filename}', 'rb') as f:
                        data = pickle.load(f)

                    if not data:
                        raise ValueError(f"Missing model_weights in data from file: {filename}")
                    # decoded_params.append(data)
                    decoded_params.append(ModelUpdate(weights=data))
                    # decoded_params.append(ModelUpdate(weights=data[0].detach().numpy()))
                else:
                    raise ValueError(
                        f"Failed to retrieve node params from link: {filename}. HTTP Status: {response.status_code}")
            except Exception as e:
                raise ValueError(f"Error retrieving data from link {filename}: {str(e)}")

        # do aggregation function here (doesn't return anything)
        self.fusion_model.update_weights(decoded_params)

        aggregate_params_weights = self.fusion_model.current_model_weights

        # aggregate_model_update = ModelUpdate(weights=np.array(aggregate_params_weights, dtype=np.float32))
        aggregate_model_update = ModelUpdate(weights=aggregate_params_weights)

        # encode params back to string
        encoded_params = self.encode_params(aggregate_model_update)


        # agg_ref = db.reference('agg_model_updates')

        # delete the old aggregated params
        # if agg_ref.get() is not None:
        #     agg_ref.delete()

        data_entry = {
            'newUpdates': encoded_params
        }

        # push agg data
        with open(f'{self.file_write_destination}/aggregator/{round_number}-agg_update.json', 'wb') as f:
            f.write(self.encode_params(data_entry))

        if self.docker_running:
            print(f'Writing to container at {f"{self.docker_file_write_destination}/aggregator/{round_number}-agg_update.json"}')
            copy_file_to_container(self.docker_container_name, f'{self.file_write_destination}/aggregator/{round_number}-agg_update.json', f'{self.docker_file_write_destination}/aggregator/{round_number}-agg_update.json')
            return f'{self.docker_file_write_destination}/aggregator/{round_number}-agg_update.json'

        return f'{self.file_write_destination}/aggregator/{round_number}-agg_update.json'

    def encode_params(self, new_model_weights):
        serialized_data = pickle.dumps(new_model_weights)
        # compressed_data = zlib.compress(serialized_data)
        # encoded_model_update = base64.b64encode(compressed_data).decode('utf-8')
        return serialized_data

    def decode_params(self, encoded_model_update):
        # compressed_data = base64.b64decode(encoded_model_update)
        # serialized_data = zlib.decompress(compressed_data)
        model_weights = pickle.loads(encoded_model_update)
        return model_weights

    def inference(self, data):
        results = self.fusion_model.fl_model.evaluate(data)
        return results
