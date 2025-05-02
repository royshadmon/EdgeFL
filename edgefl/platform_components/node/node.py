"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""

import logging
import os
import pickle
from asyncio import sleep

# import keras
import numpy as np
# from keras import layers, optimizers, models

from platform_components.EdgeLake_functions.blockchain_EL_functions import insert_policy, check_policy_inserted, \
    get_policies
from platform_components.EdgeLake_functions.mongo_file_store import copy_file_to_container, create_directory_in_container
from platform_components.EdgeLake_functions.mongo_file_store import read_file, write_file, copy_file_from_container
from platform_components.lib.logger.logger_config import configure_logging
from platform_components.helpers.LoadClassFromFile import load_class_from_file

from dotenv import load_dotenv
load_dotenv()


class Node:
    def __init__(self, replica_name, ip, port, index, module_name, module_path, logger):
        self.github_dir = os.getenv('GITHUB_DIR')
        # self.module_name = os.getenv('MODULE_NAME') # todo: modularize
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        self.edgelake_tcp_node_ip_port = f'{os.getenv("EXTERNAL_TCP_IP_PORT")}'

        self.replica_name = replica_name
        self.node_ip = ip
        self.node_port = port
        # self.index = index # index specified *only* on init; tracked for entire training process
        self.indexes = set()
        self.indexes.add(index)

        self.logger = logger
        self.logger.debug("Node initializing")


        # ===== Index-specific data
        self.indexes = set()
        # self.replica_names = {}
        self.data_batches = {} # {'index1': [], 'index2': [], ...}
        self.round_number = {}

        self.module_names = {}
        self.module_paths = {}
        self.data_handlers = {}
        self.fetch_indexes_and_modules() # TODO: maybe not do this, if user inputs existing index but different module, just warn them and use existing module

        self.file_write_destination = {}
        self.tmp_dir = {}
        self.docker_file_write_destination = {}
        # =====

        self.database_url = os.getenv("DATABASE_URL")
        self.mongo_db_name = os.getenv('MONGO_DB_NAME')
        # self.replica_name = replica_name # todo: modularize

        # init training application class reference # todo: modularize
        # training_app_path = os.path.join(self.github_dir, os.getenv('TRAINING_APPLICATION_PATH'))
        # TrainingApp_class = load_class_from_file(training_app_path, self.module_name)
        # self.data_handler = TrainingApp_class(self.replica_name) # Create an instance

        # init file write paths # todo: modularize

        # Node local data batches  # todo: modularize
        # self.data_batches = []
        # self.currentRound = 1

        # Initializing index specific data in this node
        self.initialize_index(index)
        self.set_module_at_index(index, module_name, module_path)
        self.initialize_training_app(index)
        self.initialize_file_write_paths(index)

    def initialize_index(self, index):
        self.indexes.add(index)

    def initialize_file_write_paths(self, index):
        self.file_write_destination[index] = os.path.join(self.github_dir, os.getenv("FILE_WRITE_DESTINATION"), self.replica_name)
        self.tmp_dir[index] = os.path.join(self.github_dir, os.getenv("TMP_DIR"), self.replica_name)
        if not os.path.exists(os.path.join(self.tmp_dir[index], index)):
            os.makedirs(os.path.join(self.tmp_dir[index], index))

        if os.getenv("EDGELAKE_DOCKER_RUNNING").lower() == "false":
            self.docker_running = False
        else:
            self.docker_running = True
            self.docker_file_write_destination[index] = os.path.join(os.getenv("DOCKER_FILE_WRITE_DESTINATION"), self.replica_name)
            self.docker_container_name = os.getenv("EDGELAKE_DOCKER_CONTAINER_NAME")
            create_directory_in_container(self.docker_container_name, os.path.join(self.docker_file_write_destination[index], index))
            # create_directory_in_container(self.docker_container_name, f"{self.docker_file_write_destination}/{self.replica_name}/{self.index}/")
            
    def initialize_training_app(self, index):
        try:
            training_app_path = os.path.join(self.github_dir, self.module_paths[index])
            TrainingApp_class = load_class_from_file(training_app_path, self.module_names[index])
            self.data_handlers[index] = TrainingApp_class(self.replica_name) # Create an instance at index
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    # On startup, indexes, modules, and module_paths caches are empty, so refill
    def fetch_indexes_and_modules(self):
        policies = get_policies(self.edgelake_node_url, 'index')
        for policy in policies:  # policy = {'attr1': ..., 'attr2': ..., ...}
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

    '''
    add_data_batch(data)
        - Adds passed in data to local storage
        - Used for simulating data stream
        - Assumes data is in correct format for model / datahandler
    '''
    def add_data_batch(self, index, data):
        self.data_batches[index].append(data)

    '''
    add_node_params()
        - Returns current node model parameters to edgefl via event listener
    '''
    def add_node_params(self, round_number, model_metadata, index):
        self.logger.debug("in add_node_params")
        try:
            data = f'''<my_policy = {{"{index}-a{round_number}" : {{
                                "node" : "{self.replica_name}",
                                "index": "{index}",
                                "node_type": "training",
                                "ip_port": "{self.edgelake_tcp_node_ip_port}",                                
                                "trained_params_local_path": "{model_metadata}"
            }} }}>'''

            success = False
            while not success:
                self.logger.debug("Attempting insert")
                response = insert_policy(self.edgelake_node_url, data)
                if response.status_code == 200:
                    success = True
                else:
                    sleep(np.random.randint(5,15))
                    if check_policy_inserted(self.edgelake_node_url, data):
                        success = True

            self.logger.debug(f"Submitting results for round {round_number}")
            # response = requests.post(self.edgelake_node_url, headers=headers, data=data)
            # TODO: add error check here

            return {
                'status': 'success',
                'message': 'node model parameters added successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    '''
    train_model_params(aggregator_model_params)
        - Uses updated aggregator model params and updates local model
        - Gets local data and runs training on updated model
    '''
    def train_model_params(self, aggregator_model_params_db_link, round_number, ip_ports, index):
        self.logger.debug(f"in train_model_params for round {round_number}")

        # First round initialization
        if round_number == 1 and not aggregator_model_params_db_link:
            # weights = self.local_training_handler.fl_model.get_model_update()
            weights = self.data_handlers[index].get_weights()
            # model_update = self.data_handlers[index].get_model_update()
        else:
            try:
                # Extract the key from the URL
                filename = aggregator_model_params_db_link.split('/')[-1]
                if self.docker_running:
                    response = read_file(self.edgelake_node_url, aggregator_model_params_db_link,
                                         f'{self.docker_file_write_destination[index]}/{index}/{filename}', ip_ports)
                    copy_file_from_container(os.path.join(self.tmp_dir[index], index), self.docker_container_name, f'{self.docker_file_write_destination[index]}/{index}/{filename}', f'{self.file_write_destination[index]}/{index}/{filename}')
                else:
                    response = read_file(self.edgelake_node_url, aggregator_model_params_db_link, f'{self.file_write_destination[index]}/{index}/{filename}', ip_ports)


                # response = requests.get(link)
                if response.status_code == 200:
                    sleep(1)
                    with open(
                            f'{self.file_write_destination[index]}/{index}/{filename}',
                            'rb') as f:
                        data = pickle.load(f)

                # Ensure the data is valid and decode the parameters
                if data and 'newUpdates' in data:
                    weights = self.decode_params(data['newUpdates'])
                else:
                    self.logger.error(f"Invalid data or 'newUpdates' missing in Firestore response: {data}")
                    raise ValueError(f"Invalid data or 'newUpdates' missing in Firestore response: {data}")
            except Exception as e:
                self.logger.error(f"Error getting weights: {str(e)}")
                raise

        # Update model with weights
        self.data_handlers[index].update_model(weights)

        # Train model
        # model_update = self.local_training_handler.train({})
        model_params = self.data_handlers[index].train(round_number)

        # Save and return new weights
        encoded_params = self.encode_model(model_params)
        file = f"{round_number}-replica-{self.replica_name}.pkl"
        # make sure directory exists
        os.makedirs(os.path.dirname(f"{self.file_write_destination[index]}/{index}/"), exist_ok=True)
        file_name = f"{self.file_write_destination[index]}/{index}/{file}"
        with open(f"{file_name}", "wb") as f:
            f.write(encoded_params)

        self.logger.info(f"[Round {round_number}] Step 2 Complete: model training done")
        if self.docker_running:
            self.logger.debug(f'written to container at {f"{self.docker_file_write_destination[index]}/{index}/{file}"}')
            copy_file_to_container(os.path.join(self.tmp_dir[index], index), self.docker_container_name, file_name, f"{self.docker_file_write_destination[index]}/{index}/{file}")
            return f'{self.docker_file_write_destination[index]}/{index}/{file}'
        return file_name

    def encode_model(self, model_update):
        serialized_data = pickle.dumps(model_update)
        return serialized_data

    def decode_params(self, encoded_model_update):
        model_weights = pickle.loads(encoded_model_update)
        return model_weights

    def inference(self, index):
        return self.data_handlers[index].run_inference()

    def direct_inference(self, index, data):
        return self.data_handlers[index].direct_inference(data)