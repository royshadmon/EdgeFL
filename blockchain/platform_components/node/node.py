import os
import pickle
from asyncio import sleep
import ast
from fileinput import filename

import keras
import numpy as np
from ibmfl.model.pytorch_fl_model import PytorchFLModel
from keras import layers, optimizers, models

from platform_components.EdgeLake_functions.blockchain_EL_functions import insert_policy, check_policy_inserted
from platform_components.EdgeLake_functions.mongo_file_store import copy_file_to_container, create_directory_in_container
from platform_components.data_handlers.winniio_data_handler import WinniioDataHandler
from platform_components.EdgeLake_functions.mongo_file_store import read_file, write_file, copy_file_from_container
from platform_components.data_handlers.custom_data_handler import CustomMnistPytorchDataHandler
from sklearn.metrics import accuracy_score
# import pathlib

from dotenv import load_dotenv

load_dotenv()


class Node:
    def __init__(self, model_def, replica_name, ip, port):
        self.file_write_destination = os.getenv("FILE_WRITE_DESTINATION")
        self.node_ip = ip
        self.node_port = port
        print("Node initializing")

        self.database_url = os.getenv("DATABASE_URL")
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        self.edgelake_tcp_node_ip_port = f'{os.getenv("EXTERNAL_TCP_IP_PORT")}'
        self.mongo_db_name = os.getenv('MONGO_DB_NAME')
        self.replicaName = replica_name

        if os.getenv("EDGELAKE_DOCKER_RUNNING").lower() == "false":
            self.docker_running = False
        else:
            self.docker_running = True
            self.docker_file_write_destination = os.getenv("DOCKER_FILE_WRITE_DESTINATION")
            self.docker_container_name = os.getenv("EDGELAKE_DOCKER_CONTAINER_NAME")
            create_directory_in_container(self.docker_container_name, self.docker_file_write_destination)
            create_directory_in_container(self.docker_container_name, f"{self.docker_file_write_destination}/{self.replicaName}/")

        # Node local data batches
        self.data_batches = []

        self.currentRound = 1

        # model_def == 1: PytorchFLModel
        if model_def == 1:
            model_path = os.path.join("/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain", "configs", "node", "pytorch", "pytorch_sequence.pt")

            model_spec = {
                "loss_criterion": "nn.NLLLoss",
                "model_definition": str(model_path),
                "model_name": "pytorch-nn",
                "optimizer": "optim.Adadelta"
            }

            fl_model = PytorchFLModel(model_name="pytorch-nn", model_spec=model_spec)
            self.data_handler = CustomMnistPytorchDataHandler(self.replicaName,fl_model)
        # add more model defs in elifs below
        elif model_def == 2:
            time_steps = 1

            input = layers.Input(shape=(time_steps, 6))
            hidden_layer = layers.LSTM(256, activation='relu')(input)
            output = layers.Dense(1)(hidden_layer)
            model = models.Model(input, output)

            rmse = keras.metrics.RootMeanSquaredError(name='rmse')

            model.compile(
                loss='mse',
                optimizer=optimizers.Adam(learning_rate=0.0002),
                metrics=['mse', 'mae', rmse],
            )
            print("BEFORE SET UP HANDLER")
            self.data_handler = WinniioDataHandler(self.replicaName, model)
            print("AFTER SET UP HANDLER")


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
        - Returns current node nodel parameters to blockchain via event listener
    '''

    def add_node_params(self, round_number, model_metadata):
        print("in add_node_params")

        # dbms_name = model_metadata[0]
        # table_name = model_metadata[1]
        # filename = model_metadata

        try:

            data = f'''<my_policy = {{"a{round_number}" : {{
                                "node" : "{self.replicaName}",
                                "ip_port": "{self.edgelake_tcp_node_ip_port}",                                
                                "trained_params_local_path": "{model_metadata}"
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


            # print(f"Submitting results for round {round_number}")
            # response = requests.post(self.edgelake_node_url, headers=headers, data=data)
            # TODO: add error check here
            print(f"Results submitted for round {round_number} to {self.replicaName}")

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
        - Uses updated aggreagtor model params and updates local model
        - Gets local data and runs training on updated model
    '''

    def train_model_params(self, aggregator_model_params_db_link, round_number, ip_ports):
        print(f"in train_model_params for round {round_number}")

        # First round initialization
        if round_number == 1:
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
                    copy_file_from_container(self.docker_container_name, f'{self.docker_file_write_destination}/{self.replicaName}/{filename}', f'{self.file_write_destination}/{self.replicaName}/{filename}')
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
                    raise ValueError(f"Invalid data or 'newUpdates' missing in Firestore response: {data}")
            except Exception as e:
                print(f"Error getting weights: {str(e)}")
                raise

        # Update model with weights
        self.data_handler.update_model(weights)

        # Train model
        # model_update = self.local_training_handler.train({})
        model_params = self.data_handler.train(round_number)

        # Save and return new weights
        encoded_params = self.encode_model(model_params)
        file = f"{round_number}-replica-{self.replicaName}.pkl"
        # make sure directory exists
        os.makedirs(os.path.dirname(f"{self.file_write_destination}/{self.replicaName}/"), exist_ok=True)
        file_name = f"{self.file_write_destination}/{self.replicaName}/{file}"
        with open(f"{file_name}", "wb") as f:
            f.write(encoded_params)

        if self.docker_running:
            print(f'written to container at {f"{self.docker_file_write_destination}/{self.replicaName}/{file}"}')
            copy_file_to_container(self.docker_container_name, file_name, f"{self.docker_file_write_destination}/{self.replicaName}/{file}")
            return f'{self.docker_file_write_destination}/{self.replicaName}/{file}'
        return file_name



    def encode_model(self, model_update):
        serialized_data = pickle.dumps(model_update)
        # compressed_data = zlib.compress(serialized_data)
        # encoded_model_update = base64.b64encode(compressed_data).decode('utf-8')
        return serialized_data

    def decode_params(self, encoded_model_update):
        # compressed_data = base64.b64decode(encoded_model_update)
        # serialized_data = zlib.decompress(compressed_data)
        # model_weights = pickle.loads(serialized_data)
        model_weights = pickle.loads(encoded_model_update)
        return model_weights

    # NOTE:
    # - training with one node for 12 rounds resulted in accuracy of ~44.75%
    # - training with two nodes for 12 rounds resulted in accuracy of ~55.17%
    def inference(self):
        return self.data_handler.run_inference()
