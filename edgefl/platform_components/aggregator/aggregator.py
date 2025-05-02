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
from threading import Lock
from dotenv import load_dotenv

from platform_components.EdgeLake_functions.mongo_file_store import copy_file_to_container, create_directory_in_container
from platform_components.EdgeLake_functions.blockchain_EL_functions import insert_policy, \
    check_policy_inserted, delete_policy, get_policy_id_by_name, get_policies
from platform_components.EdgeLake_functions.mongo_file_store import read_file, write_file, copy_file_from_container

from platform_components.lib.modules.local_model_update import LocalModelUpdate

from platform_components.helpers.LoadClassFromFile import load_class_from_file


load_dotenv()


class Aggregator:
    def __init__(self, ip, port, logger):
        self.github_dir = os.getenv('GITHUB_DIR')
        # self.module_name = os.getenv('MODULE_NAME')
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        self.edgelake_tcp_node_ip_port = f'{os.getenv("EXTERNAL_TCP_IP_PORT")}'

        self.agg_name = os.getenv("AGG_NAME")

        self.server_ip = ip
        self.server_port = port
        # self.index = '' # right now, specified *only* on init; tracked for entire training process
        
        self.logger = logger
        self.logger.debug("Aggregator initializing")

        # ===== Index-specific data
        self.indexes = set()
        self.node_urls = {}
        self.node_count = {}
        self.lock = Lock()
        self.minParams = {}
        self.round_number = {}

        # These will be cached on aggregator startup
        self.module_names = {}
        self.module_paths = {}
        self.training_apps = {}
        self.fetch_indexes_and_modules()

        # Multi-training means processes write to their own file write paths
        self.file_write_destination = {}
        self.tmp_dir = {}
        self.docker_file_write_destination = {}
        # =====

        # Initialize Firebase database connection
        self.database_url = os.getenv('DATABASE_URL')

        # init training application class reference
        # training_app_path = os.path.join(self.github_dir, os.getenv('TRAINING_APPLICATION_PATH'))
        # TrainingApp_class = load_class_from_file(training_app_path, self.module_name)
        # self.training_app = TrainingApp_class('aggregator') # Create an instance

        if os.getenv("EDGELAKE_DOCKER_RUNNING").lower() == "false":
            self.docker_running = False
        else:
            self.docker_running = True


    def initialize_file_write_paths(self, index):
        # Each index has only one module, so they'll also have only one file_write_path for them
        try:
            self.file_write_destination[index] = os.path.join(self.github_dir, os.getenv("FILE_WRITE_DESTINATION"), self.agg_name)

            if not os.path.exists(os.path.join(self.file_write_destination[index], index)):
                os.makedirs(os.path.dirname(
                    f"{self.file_write_destination[index]}/{index}/"),
                    exist_ok=True)

            self.tmp_dir[index] = os.path.join(self.github_dir, os.getenv("TMP_DIR"), self.agg_name)
            if not os.path.exists(os.path.join(self.tmp_dir[index], index)):
                os.makedirs(os.path.join(self.tmp_dir[index], index), exist_ok=True)

            if self.docker_running:
                self.docker_file_write_destination[index] = os.path.join(os.getenv("DOCKER_FILE_WRITE_DESTINATION"), self.agg_name)
                self.docker_container_name = os.getenv("EDGELAKE_DOCKER_CONTAINER_NAME")
                create_directory_in_container(self.docker_container_name, os.path.join(self.docker_file_write_destination[index], index))
                # create_directory_in_container(self.docker_container_name,
                #                               f"{self.docker_file_write_destination}/aggregator/")

            return {
                    'status': 'success',
                    'message': 'file write paths initialized'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def initialize_index_on_blockchain(self, index, module_name, module_path):
        if self.get_index_in_blockchain(index):
            return {
                'status': 'error',
                'message': 'index already initialized'
            }

        try:
            data = f'''<my_policy = {{"index" : {{
                                        "name": "{index}",
                                        "module_name": "{module_name}",
                                        "module_path": "{module_path}"
            }} }}>'''
            success = False
            while not success:
                response = insert_policy(self.edgelake_node_url, data)
                if response.status_code == 200:
                    success = True
                else:
                    sleep(np.random.randint(2, 5))

                    if check_policy_inserted(self.edgelake_node_url, data):
                        success = True

            if success:
                return {
                    'status': 'success',
                    'message': 'index initialized onto the blockchain'
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

    def initialize_training_app(self, index):
        try:
            training_app_path = os.path.join(self.github_dir, self.module_paths[index])
            TrainingApp_class = load_class_from_file(training_app_path, self.module_names[index])
            self.training_apps[index] = TrainingApp_class('aggregator') # Create an instance at index
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    # On startup, indexes, modules, and module_paths caches are empty, so refill
    def fetch_indexes_and_modules(self):
        policies = get_policies(self.edgelake_node_url, 'index')
        for policy in policies: # policy = {'attr1': ..., 'attr2': ..., ...}
            index = policy['name']
            self.indexes.add(index)
            self.module_names[index] = policy['module_name']
            self.module_paths[index] = policy['module_path']

    # Each index has one training app model
    def set_module_at_index(self, index, module_name, module_path):
        try:
            if index in self.module_names or self.get_index_in_blockchain(index):
                self.logger.info(f'Index "{index}" already has a module: "{self.module_names[index]}"')
                return {
                    'status': 'error',
                    'message': f'Index "{index}" already has a module: "{self.module_names[index]}"'
                }

            self.module_names[index] = module_name
            self.module_paths[index] = module_path
            self.logger.info(f'Added module "{module_name}" to index "{index}"')
            return {
                'status': 'success',
                'message': f'Added module "{module_name}" to index {index}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    # Gets specified index in blockchain if it exists, otherwise returns None
    def get_index_in_blockchain(self, index):
        where_condition = f"where name = {index}"
        policies = get_policies(self.edgelake_node_url, "index", where_condition)
        if not policies:
            return None

        if len(policies) > 1: # dev check
            raise Exception(f"Multiple instances of index {index} found in the blockchain")

        return index

    # Deletes and inserts index-rx with updated initParams ('blockchain update to' not working)
    def store_most_recent_agg_params(self, initParams_link, index):
        try:
            policy_name = f"{index}-r"
            old_policy_id = get_policy_id_by_name(self.edgelake_node_url, policy_name)

            # Deleting old policy
            delete_success = False
            while old_policy_id and not delete_success:
                response = delete_policy(self.edgelake_node_url, old_policy_id)
                if response.status_code == 200:
                    delete_success = True
                else:
                    sleep(np.random.randint(1,3))

            # Inserting policy back in with updated initParams link
            data = f'''<my_policy = {{"{policy_name}" : {{
                                                    "index" : "{index}",
                                                    "node_type": "aggregator",
                                                    "initParams": "{initParams_link}",
                                                    "ip_port": "{self.edgelake_tcp_node_ip_port}"
                                          }} }}>'''
            insert_success = False
            while not insert_success:
                response = insert_policy(self.edgelake_node_url, data)
                if response.status_code == 200:
                    insert_success = True
                else:
                    sleep(np.random.randint(2, 5))

                    if check_policy_inserted(self.edgelake_node_url, data):
                        insert_success = True

            if insert_success:
                return {
                    'status': 'success',
                    'message': f'Successfully updated most recent aggregated model file at policy {index}-r'
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

    # function to call the start round function
    def start_round(self, initParams_link, round_number, index):
        try:
            # Format data exactly like the example curl command but with your values
            # NOTE: ask why are we adding the node num from agg
            data = f'''<my_policy = {{"{index}-r{round_number}" : {{
                                        "index" : "{index}",
                                        "node_type": "aggregator",
                                        "initParams": "{initParams_link}",
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

    def aggregate_model_params(self, node_param_download_links, ip_ports, round_number, index):
        # use the node_param_download_links to get all the file
        # in the form of tuples, like ["('blobs_admin', 'node_model_updates', '1-replica-node1.pkl')"]
        # node_ref = db.reference('node_model_updates')

        decoded_params = []
        # Loop through each provided download link to retrieve node parameter objects
        for i, path in enumerate(node_param_download_links):
            try:
                # make sure directory exists
                filename = path.split('/')[-1]

                local_path = f'{self.file_write_destination[index]}/{index}/{filename}'
                if self.docker_running:
                    docker_file_path = f'{self.docker_file_write_destination[index]}/{index}/{filename}'
                    response = read_file(self.edgelake_node_url, path,
                                         docker_file_path, ip_ports[i])
                    copy_file_from_container(os.path.join(self.tmp_dir[index], index), self.docker_container_name,
                                        docker_file_path,
                                        local_path)
                else:
                    response = read_file(self.edgelake_node_url, path,
                                     local_path, ip_ports[i])

                if response.status_code == 200:
                    sleep(1)
                    with open(local_path, 'rb') as f:
                        data = pickle.load(f)

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
                raise ValueError(f"Error retrieving data from link {filename}: {str(e)}")

        aggregate_params_weights = self.training_apps[index].aggregate_model_weights(decoded_params)

        # aggregate_params_weights = [np.array(aggregate_params_weights[0], dtype=np.float32)]

        aggregate_model_update = LocalModelUpdate(weights=aggregate_params_weights)

        # encode params back to string
        encoded_params = self.encode_params(aggregate_model_update)

        data_entry = {
            'newUpdates': encoded_params
        }

        # push agg data
        # TODO: will this work on windows?
        file_write_path = f'{self.file_write_destination[index]}/{index}/{round_number}-{self.agg_name}_update.json'

        with open(file_write_path, 'wb') as f:
            f.write(self.encode_params(data_entry))

        # print(f"Model aggregation for round {round_number} complete")
        if self.docker_running:
            docker_file_write_path = f'{self.docker_file_write_destination[index]}/{index}/{round_number}-{self.agg_name}_update.json'
            # print(f'Writing to container at {f"{self.docker_file_write_destination}/aggregator/{round_number}-agg_update.json"}')
            copy_file_to_container(os.path.join(self.tmp_dir[index],index), self.docker_container_name, file_write_path, docker_file_write_path)
            return docker_file_write_path

        return file_write_path

    def encode_params(self, new_model_weights):
        serialized_data = pickle.dumps(new_model_weights)
        return serialized_data

    def decode_params(self, encoded_model_update):
        model_weights = pickle.loads(encoded_model_update)
        return model_weights