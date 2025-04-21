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

from platform_components.EdgeLake_functions.blockchain_EL_functions import insert_policy, check_policy_inserted
from platform_components.EdgeLake_functions.mongo_file_store import copy_file_to_container, create_directory_in_container
from platform_components.EdgeLake_functions.mongo_file_store import read_file, write_file, copy_file_from_container
from platform_components.lib.logger.logger_config import configure_logging
from platform_components.helpers.LoadClassFromFile import load_class_from_file

from dotenv import load_dotenv
load_dotenv()


class Node:
    def __init__(self, replica_name, ip, port, index, logger):
        self.github_dir = os.getenv('GITHUB_DIR')
        self.module_name = os.getenv('MODULE_NAME')
        self.node_ip = ip
        self.node_port = port
        self.index = index # index specified *only* on init; tracked for entire training process

        self.logger = logger
        self.logger.debug("Node initializing")

        self.database_url = os.getenv("DATABASE_URL")
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        self.edgelake_tcp_node_ip_port = f'{os.getenv("EXTERNAL_TCP_IP_PORT")}'
        self.mongo_db_name = os.getenv('MONGO_DB_NAME')
        self.replicaName = replica_name

        # init training application class reference
        training_app_path = os.path.join(self.github_dir, os.getenv('TRAINING_APPLICATION_PATH'))
        TrainingApp_class = load_class_from_file(training_app_path, self.module_name)
        self.data_handler = TrainingApp_class(self.replicaName)  # Create an instance

        # init file write paths
        self.file_write_destination = os.path.join(self.github_dir, os.getenv("FILE_WRITE_DESTINATION"),
                                                   self.module_name, self.index)
        self.tmp_dir = os.path.join(self.github_dir, os.getenv("TMP_DIR"), self.module_name, self.index)
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)

        if os.getenv("EDGELAKE_DOCKER_RUNNING").lower() == "false":
            self.docker_running = False
        else:
            self.docker_running = True
            self.docker_file_write_destination = os.path.join(os.getenv("DOCKER_FILE_WRITE_DESTINATION"), self.module_name, self.index)
            self.docker_container_name = os.getenv("EDGELAKE_DOCKER_CONTAINER_NAME")
            create_directory_in_container(self.docker_container_name, self.docker_file_write_destination)
            create_directory_in_container(self.docker_container_name, f"{self.docker_file_write_destination}/{self.replicaName}/")

        # Node local data batches
        self.data_batches = []
        self.currentRound = 1

    '''
    add_data_batch(data)
        - Adds passed in data to local storage
        - Used for simulating data stream
        - Assumes data is in correct format for model / datahandler
    '''
    def add_data_batch(self, data):
        self.data_batches.append(data)

    '''
    add_node_params()
        - Returns current node model parameters to edgefl via event listener
    '''
    def add_node_params(self, round_number, model_metadata, index):
        self.logger.debug("in add_node_params")
        try:
            data = f'''<my_policy = {{"{index}-a{round_number}" : {{
                                "node" : "{self.replicaName}",
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
            weights = self.data_handler.get_weights()
            # model_update = self.data_handler.get_model_update()
        else:
            try:
                # Extract the key from the URL
                filename = aggregator_model_params_db_link.split('/')[-1]
                if self.docker_running:
                    response = read_file(self.edgelake_node_url, aggregator_model_params_db_link,
                                         f'{self.docker_file_write_destination}/{self.replicaName}/{filename}', ip_ports)
                    copy_file_from_container(self.tmp_dir, self.docker_container_name, f'{self.docker_file_write_destination}/{self.replicaName}/{filename}', f'{self.file_write_destination}/{self.replicaName}/{filename}')
                else:
                    response = read_file(self.edgelake_node_url, aggregator_model_params_db_link,f'{self.file_write_destination}/{self.replicaName}/{filename}', ip_ports)

                # response = requests.get(link)
                if response.status_code == 200:
                    sleep(1)
                    with open(
                            f'{self.file_write_destination}/{self.replicaName}/{filename}',
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
        self.data_handler.update_model(weights)

        # Train model
        # model_update = self.local_training_handler.train({})
        model_params = self.data_handler.train(round_number)

        # Save and return new weights
        encoded_params = self.encode_model(model_params)
        file = f"{index}-{round_number}-replica-{self.replicaName}.pkl"
        # make sure directory exists
        os.makedirs(os.path.dirname(f"{self.file_write_destination}/{self.replicaName}/"), exist_ok=True)
        file_name = f"{self.file_write_destination}/{self.replicaName}/{file}"
        with open(f"{file_name}", "wb") as f:
            f.write(encoded_params)

        self.logger.info(f"[Round {round_number}] Step 2 Complete: model training done")
        if self.docker_running:
            self.logger.debug(f'written to container at {f"{self.docker_file_write_destination}/{self.replicaName}/{file}"}')
            copy_file_to_container(self.tmp_dir, self.docker_container_name, file_name, f"{self.docker_file_write_destination}/{self.replicaName}/{file}")
            return f'{self.docker_file_write_destination}/{self.replicaName}/{file}'
        return file_name

    def encode_model(self, model_update):
        serialized_data = pickle.dumps(model_update)
        return serialized_data

    def decode_params(self, encoded_model_update):
        model_weights = pickle.loads(encoded_model_update)
        return model_weights

    def inference(self):
        return self.data_handler.run_inference()

    def direct_inference(self, data):
        return self.data_handler.direct_inference(data)