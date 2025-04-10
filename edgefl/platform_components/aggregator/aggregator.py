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

from platform_components.EdgeLake_functions.mongo_file_store import copy_file_to_container, create_directory_in_container
from platform_components.EdgeLake_functions.blockchain_EL_functions import insert_policy, \
    check_policy_inserted
from platform_components.EdgeLake_functions.mongo_file_store import read_file, write_file, copy_file_from_container

from platform_components.lib.modules.local_model_update import LocalModelUpdate

from platform_components.helpers.LoadClassFromFile import load_class_from_file

CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')

load_dotenv()


class Aggregator:
    def __init__(self, ip, port):
        self.github_dir = os.getenv('GITHUB_DIR')
        self.file_write_destination = os.path.join(self.github_dir, os.getenv("FILE_WRITE_DESTINATION"))

        self.tmp_dir = os.path.join(self.github_dir, os.getenv("TMP_DIR"))
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)

        self.server_ip = ip
        self.server_port = port

        # init training application class reference
        training_app_path = os.path.join(self.github_dir, os.getenv('TRAINING_APPLICATION_PATH'))
        module_name = os.getenv('MODULE_NAME')

        TrainingApp_class = load_class_from_file(training_app_path, module_name)

        self.training_app = TrainingApp_class('aggregator')  # Create an instance

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


    # function to call the start round function from the smart contract
    def start_round(self, initParamsLink, roundNumber):
        try:

            # NOTE: ask why are we adding the node num from agg
            data = f'''<my_policy = {{"r{roundNumber}" : {{
                                        "initParams": "{initParamsLink}",
                                        "ip_port": "{self.edgelake_tcp_node_ip_port}"                                
                              }} }}>'''
            success = False
            while not success:
                # print("Attempting insert")
                response = insert_policy(self.edgelake_node_url, data)
                if response.status_code == 200:
                    success = True
                else:
                    sleep(np.random.randint(5,15))

                    if check_policy_inserted(self.edgelake_node_url, data):
                        success = True

            # print(f"Training initialized with {roundNumber} rounds")

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
                                         f'{self.docker_file_write_destination}/aggregator/{filename}', 
                                         ip_ports[i], self.docker_container_name)

                    copy_file_from_container(self.tmp_dir, self.docker_container_name,
                                        f'{self.docker_file_write_destination}/aggregator/{filename}',
                                        f'{self.file_write_destination}/aggregator/{filename}')
                else:
                    response = read_file(self.edgelake_node_url, path,
                                     f'{self.file_write_destination}/aggregator/{filename}', ip_ports[i])

                if response.status_code == 200:
                    sleep(1)
                    # with open(f'{self.file_write_destination}/aggregator/{filename}', 'rb') as f:
                    #     data = pickle.load(f)

                    with open(f'{self.file_write_destination}/aggregator/{filename}', 'rb') as f:
                        data = bytearray()
                        while chunk := f.read(1024):
                            data.extend(chunk)
                        data = pickle.loads(data)

                    if not data:
                        raise ValueError(f"Missing model_weights in data from file: {filename}")
                    # decoded_params.append(data)

                    # decoded_params.append({'weights': pickle.dumps(data)})
                    decoded_params.append(LocalModelUpdate(weights=data))
                    # decoded_params.append(LocalModelUpdate(weights=data[0].detach().numpy()))
                else:
                    raise ValueError(
                        f"Failed to retrieve node params from link: {filename}. HTTP Status: {response.status_code}")
            except Exception as e:
                if os.path.exists(f'{self.file_write_destination}/aggregator/{filename}'):
                    os.remove(f'{self.file_write_destination}/aggregator/{filename}')
                raise ValueError(f"Error retrieving data from link {filename}: {str(e)}")


        aggregate_params_weights = self.training_app.aggregate_model_weights(decoded_params)

        # aggregate_params_weights = [np.array(aggregate_params_weights[0], dtype=np.float32)]

        aggregate_model_update = LocalModelUpdate(weights=aggregate_params_weights)

        # encode params back to string
        encoded_params = self.encode_params(aggregate_model_update)

        data_entry = {
            'newUpdates': encoded_params
        }


        # push agg data
        with open(f'{self.file_write_destination}/aggregator/{round_number}-agg_update.json', 'wb') as f:
            f.write(self.encode_params(data_entry))
            f.flush()  # Ensure data is written to buffer
            os.fsync(f.fileno())  # Ensure data is written to disk


        # print(f"Model aggregation for round {round_number} complete")
        if self.docker_running:
            # print(f'Writing to container at {f"{self.docker_file_write_destination}/aggregator/{round_number}-agg_update.json"}')
            copy_file_to_container(self.tmp_dir, self.docker_container_name, f'{self.file_write_destination}/aggregator/{round_number}-agg_update.json', f'{self.docker_file_write_destination}/aggregator/{round_number}-agg_update.json')
            return f'{self.docker_file_write_destination}/aggregator/{round_number}-agg_update.json'

        return f'{self.file_write_destination}/aggregator/{round_number}-agg_update.json'

    def encode_params(self, new_model_weights):
        serialized_data = pickle.dumps(new_model_weights)
        return serialized_data

    def decode_params(self, encoded_model_update):
        model_weights = pickle.loads(encoded_model_update)
        return model_weights
