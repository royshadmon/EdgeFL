import os
import pickle
from asyncio import sleep
import ast
import firebase_admin
import keras
import numpy as np
import torch
from firebase_admin import credentials
from ibmfl.party.training.local_training_handler import LocalTrainingHandler
from ibmfl.model.pytorch_fl_model import PytorchFLModel
# from tensorflow.python.keras import optimizers
from keras import layers, optimizers, models

from EdgeLake_functions.mongo_file_store import read_file, write_file
from blockchain.platform_components.EdgeLake_functions.blockchain_EL_functions import force_insert_policy
from blockchain.platform_components.EdgeLake_functions.mongo_file_store import write_file
from data_handlers.custom_data_handler import CustomMnistPytorchDataHandler
from sklearn.metrics import accuracy_score
# import pathlib

from dotenv import load_dotenv

load_dotenv()


class Node:
    def __init__(self, model_def, replica_name, ip, port):
        self.node_ip = ip
        self.node_port = port
        print("Node initializing")

        self.database_url = os.getenv("DATABASE_URL")
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        self.edgelake_tcp_node_ip_port = f'{os.getenv("EXTERNAL_TCP_IP_PORT")}'

        self.replicaName = replica_name

        # Node local data batches
        self.data_batches = []

        self.currentRound = 1

        # current_dir = os.path.dirname(os.path.abspath(__file__))

        # data_path = os.getenv("DATASET_PATH")
        # data_config = {
        #     "npz_file": str(data_path)
        # }

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
            data_handler = CustomMnistPytorchDataHandler(self.replicaName)
            # data_handler = MnistPytorchDataHandler(data_config=data_config)
            self.local_training_handler = LocalTrainingHandler(fl_model=fl_model, data_handler=data_handler)
        # add more model defs in elifs below
        elif model_def == 2:
            pass
            # input = layers.Input(shape=(time_steps, 10))
            # hidden_layer = layers.LSTM(256, activation='relu')(input)
            # output = layers.Dense(1)(hidden_layer)
            # model = models.Model(input, output)
            #
            # rmse = keras.metrics.RootMeanSquaredError(name='rmse')
            # model.compile(
            #     loss= 'mse',
            #     optimizer= optimizers.Adam(learning_rate=0.0002),
            #     metrics= ['mse', 'mae', rmse]
            # )
            #
            # data_handlers = win
        # model_def == 2: Sklearn and so on

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

        dbms_name = model_metadata[0]
        table_name = model_metadata[1]
        filename = model_metadata

        try:

            data = f'''<my_policy = {{"a{round_number}" : {{
                                "node" : "{self.replicaName}",
                                "ip_port": "{self.edgelake_tcp_node_ip_port}",
                                "trained_params_dbms": "{dbms_name}",
                                "trained_params_table": "{table_name}",
                                "trained_params_filename": "{filename}"
            }} }}>'''

            success = False
            while not success:
                print("Attempting insert")
                response = force_insert_policy(self.edgelake_node_url, data)
                if response.status_code == 200:
                    success = True
                elif response.status_code == 400:
                    if response.content.decode().__contains__("Duplicate blockchain object id"):
                        success = True
                else:
                    sleep(1)


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
            weights = self.local_training_handler.fl_model.get_model_update()
        else:
            try:
                # Extract the key from the URL

                model_updates_key = ast.literal_eval(aggregator_model_params_db_link.split('/')[-1])

                response = read_file(self.edgelake_node_url, model_updates_key[0], model_updates_key[1], model_updates_key[2],
                                     f'/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/{self.replicaName}/{model_updates_key[2]}',
                                     ip_ports)
                # response = requests.get(link)
                if response.status_code == 200:
                    sleep(1)
                    with open(
                            f'/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/{self.replicaName}/{model_updates_key[2]}',
                            'rb') as f:
                        data = pickle.load(f)

                # Reference the database path and retrieve the data
                # agg_data_ref = db.reference(f'agg_model_updates/{model_updates_key}')
                # data = agg_data_ref.get()

                # Ensure the data is valid and decode the parameters
                if data and 'newUpdates' in data:
                    weights = self.decode_params(data['newUpdates'])
                else:
                    raise ValueError(f"Invalid data or 'newUpdates' missing in Firestore response: {data}")
            except Exception as e:
                print(f"Error getting weights: {str(e)}")
                raise

        # Update model with weights
        self.local_training_handler.update_model(weights)

        print("about to load data")
        # self.local_training_handler.data_handler.load_dataset(nb_points=5)

        # load new data
        (x_train, y_train), (x_test, y_test) = self.local_training_handler.data_handler.load_dataset(
            node_name=self.replicaName, round_number=round_number)
        self.local_training_handler.data_handler.x_train = x_train
        self.local_training_handler.data_handler.y_train = y_train
        self.local_training_handler.data_handler.x_test = x_test
        self.local_training_handler.data_handler.y_test = y_test


        # Train model
        model_update = self.local_training_handler.train({})

        # Save and return new weights
        encoded_params = self.encode_model(model_update)
        file = f"{round_number}-replica-{self.replicaName}.pkl"
        # make sure directory exists
        os.makedirs(os.path.dirname(f"/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/{self.replicaName}/"), exist_ok=True)
        file_name = f"/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/{self.replicaName}/{file}"
        with open(f"{file_name}", "wb") as f:
            f.write(encoded_params)


        response = write_file(self.edgelake_node_url, 'blobs_admin', 'node_model_updates', file_name)

        # data_pushed = db.reference('node_model_updates').push({
        #     'replicaName': self.replicaName,
        #     'model_update': encoded_params
        # })

        # return f"{self.database_url}/node_model_updates/{data_pushed.key}.json"
        return "blobs_admin", "node_model_updates", file

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
        x_test_images, y_test_labels = self.local_training_handler.data_handler.get_all_test_data(self.replicaName)

        # SAMPLE CODE FOR HOW TO RUN PREDICT AND GET NON VECTOR OUTPUT: https://github.com/IBM/federated-learning-lib/blob/main/notebooks/crypto_fhe_pytorch/pytorch_classifier_p0.ipynb
        # y_pred = np.array([])
        # for i_samples in range(sample_count):
        #     pred = party.fl_model.predict(
        #         torch.unsqueeze(torch.from_numpy(test_digits[i_samples]), 0))
        #     y_pred = np.append(y_pred, pred.argmax())
        # acc = accuracy_score(y_true, y_pred) * 100

        y_pred = np.array([])
        sample_count = x_test_images.shape[0] # number of test samples

        for i_samples in range(sample_count):
            # Get prediction for a single test sample
            pred = self.local_training_handler.fl_model.predict(
                torch.unsqueeze(torch.from_numpy(x_test_images[i_samples]), 0)
            )

            # Append the predicted class (argmax) to y_pred
            y_pred = np.append(y_pred, pred.argmax())

        acc = accuracy_score(y_test_labels, y_pred) * 100

        return acc