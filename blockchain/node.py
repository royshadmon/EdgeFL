import base64
import os
import json
import pickle
import zlib
import firebase_admin
from firebase_admin import credentials, db
from web3 import Web3
from ibmfl.party.training.local_training_handler import LocalTrainingHandler
from ibmfl.util.data_handlers.mnist_pytorch_data_handler import MnistPytorchDataHandler
from ibmfl.model.pytorch_fl_model import PytorchFLModel
import requests

from dotenv import load_dotenv
load_dotenv()

class Node:
    def __init__(self, contract_address, provider_url, private_key, config, replica_name):

        self.database_url = os.getenv('DATABASE_URL')

        cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS'))
        firebase_admin.initialize_app(cred, {
            'databaseURL': self.database_url
        })

        self.replicaName = replica_name

        # Node local data batches
        self.data_batches = []

        # IBM FL LocalTrainingHandler
        self.config = config

        # USE MNIST DATASET FOR TESTING THIS FUNCTIONALITY
        # hard code for now for testing
        model_spec = {
            "loss_criterion": "nn.NLLLoss",
            "model_definition": f"{os.getenv("MODEL_DEFINITION")}",
            "model_name": "pytorch-nn",
            "optimizer": "optim.Adadelta"
        }
        data_config = {
            "npz_file": f"{os.getenv("DATA_CONFIG")}",
        }

        fl_model = PytorchFLModel(model_name="pytorch-nn", model_spec=model_spec)
        data_handler = MnistPytorchDataHandler(data_config=data_config)
        self.local_training_handler = LocalTrainingHandler(fl_model=fl_model, data_handler=data_handler)

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

    def add_node_params(self, round_number, newly_trained_params_db_link):

        try:
            headers = {
                "Content-Type": "text/plain",
                "command": "blockchain insert where policy = !my_policy and local = true and blockchain = optimism",
            }

            # Define the data payload
            data = f'''<my_policy = {{"r{round_number}" : {{
                        "trained_params": {newly_trained_params_db_link},
                        "replica_name": {self.replicaName}
                 }}
             }}>'''

            response = requests.post(os.getenv("EXTERNAL_IP"), headers=headers, data=data)

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


    def train_model_params(self, aggregator_model_params_db_link, round_number):
        # if it's the first round,
        if round_number == 1:
            initial_model_update = self.local_training_handler.fl_model.get_model_update()
            # Update local model with sent model params
            self.local_training_handler.update_model(initial_model_update)
        else:
            # Use the provided database link to fetch the aggregated model update
            try:
                response = requests.get(aggregator_model_params_db_link)
                response.raise_for_status()  # Raise an error for bad HTTP response
                data = response.json()  # Parse the JSON response
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Error fetching model update from {aggregator_model_params_db_link}: {str(e)}")

            # Assuming 'newUpdates' is the key for the model update in the JSON response
            model_update_encoded = data.get('newUpdates')
            if not model_update_encoded:
                raise ValueError(f"Missing 'newUpdates' in the response from {aggregator_model_params_db_link}")

            # Decode the model
            decoded_weights = self.decode_params(model_update_encoded)

            # Update model
            self.local_training_handler.update_model(decoded_weights)

        # Load local data
        self.local_training_handler.data_handler.load_dataset(nb_points=50)

        # Do local training
        model_update = self.local_training_handler.train({})

        # The node parameters part of model_update needs to be encoded to a string before being returned
        encoded_params_compressed = self.encode_model(model_update)

        # Reference to database
        ref = db.reference('node_model_updates')

        # Create the data entry
        data_entry = {
            'replicaName': self.replicaName,
            'model_update': encoded_params_compressed
        }

        # Push the data
        data_pushed = ref.push(data_entry)

        # Get the link to the stored object
        object_url = f"{self.database_url}/node_model_updates/{data_pushed.key}.json"

        return object_url

    def encode_model(self, model_update):
        serialized_data = pickle.dumps(model_update)
        compressed_data = zlib.compress(serialized_data)
        encoded_model_update = base64.b64encode(compressed_data).decode('utf-8')
        return encoded_model_update

    def decode_params(self, encoded_model_update):
        compressed_data = base64.b64decode(encoded_model_update)
        serialized_data = zlib.decompress(compressed_data)
        model_weights = pickle.loads(serialized_data)
        return model_weights
