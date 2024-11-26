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
# import pathlib

from dotenv import load_dotenv
load_dotenv()

class Node:
    def __init__(self, config, replica_name):

        print("Node initializing")

        self.database_url = os.getenv('DATABASE_URL')

        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS'))
            firebase_admin.initialize_app(cred, {
                'databaseURL': self.database_url
            })

        self.replicaName = replica_name

        # Node local data batches
        self.data_batches = []

        # IBM FL LocalTrainingHandler
        self.config = config

        self.currentRound = 1
        # current_dir = pathlib.Path(__file__).parent.resolve()
        current_dir = os.path.dirname(os.path.abspath(__file__))

        data_path = os.path.join(current_dir, "data", "mnist", "data_party0.npz")
        model_path = os.path.join(current_dir, "configs", "node", "pytorch", "pytorch_sequence.pt")
        


        # USE MNIST DATASET FOR TESTING THIS FUNCTIONALITY
        # hard code for now for testing
        model_spec = {
            "loss_criterion": "nn.NLLLoss",
            "model_definition": str(model_path),
            "model_name": "pytorch-nn",
            "optimizer": "optim.Adadelta"
        }
        data_config = {
            "npz_file": str(data_path)
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
        print("in add_node_params") 

        try:
            external_ip = os.getenv("EXTERNAL_IP")
            url = f'http://{external_ip}:32049'
            
            headers = {
                'User-Agent': 'AnyLog/1.23',
                'Content-Type': 'text/plain',
                'command': 'blockchain insert where policy = !my_policy and local = true and blockchain = optimism'
            }

            data = f'''<my_policy = {{"a{round_number}" : {{
                    "node" : "{self.replicaName}",
                    "trained_params": "{newly_trained_params_db_link}"
}} }}>'''

            # print(f"Submitting results for round {round_number}")
            response = requests.post(url, headers=headers, data=data)
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
    def train_model_params(self, aggregator_model_params_db_link, round_number):
        print(f"in train_model_params for round {round_number}")
        
        # First round initialization
        if round_number == 1:
            weights = self.local_training_handler.fl_model.get_model_update()
        else:
            try:
                # Get model weights from Firebase
                model_updates_key = aggregator_model_params_db_link.split('/')[-1].replace('.json', '')
                data = db.reference(f'node_model_updates/{model_updates_key}').get()
                weights = self.decode_params(data['model_update'])
            except Exception as e:
                print(f"Error getting weights: {str(e)}")
                raise

        # Update model with weights
        self.local_training_handler.update_model(weights)
        
        # Train model
        self.local_training_handler.data_handler.load_dataset(nb_points=50)
        model_update = self.local_training_handler.train({})
        
        # Save and return new weights
        encoded_params = self.encode_model(model_update)
        data_pushed = db.reference('node_model_updates').push({
            'replicaName': self.replicaName,
            'model_update': encoded_params
        })
        
        return f"{self.database_url}/node_model_updates/{data_pushed.key}.json"

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
