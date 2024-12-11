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
from custom_data_handler import CustomMnistPytorchDataHandler
import requests
import torch
import time
# import pathlib

from dotenv import load_dotenv

load_dotenv()

def decode_from_base64(data):
        """Decode Base64 data to binary or text."""
        return base64.b64decode(data)


class Node:
    def __init__(self, firebase_model_path, firebase_datahandler_path, replica_name):

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

        self.currentRound = 1

        # download model from firebase
        self.fl_model = self.load_firebase_model(firebase_model_path);
        # download datahandler from firebase
        self.data_handler = self.load_firebase_datahandler(firebase_datahandler_path);
    
        # create the local training handler
        self.local_training_handler = LocalTrainingHandler(fl_model=self.fl_model, data_handler=self.data_handler)


   

    def load_firebase_model(self, firebase_model_path): 
 
        # get model_data from firebase
        firebase_model_ref = db.reference(firebase_model_path)
        model_data = firebase_model_ref.get()
        if model_data is None:
            print("Error: No model data found in Firebase.")
            return

        print('Downloaded model_data from Firebase')

        # derive fields, then decode source code and weights 
        model_source_code = decode_from_base64(model_data["source_code"]).decode("utf-8")
        model_weights = decode_from_base64(model_data["weights"])
        init_params = model_data.get("init_params", None)
        model_specs = model_data.get("model_spec", None)

        # Save the downloaded weights to a file-- necessary to load the model later 
        downloaded_weights_path = "downloaded_model_weights.pt"
        with open(downloaded_weights_path, "wb") as f:
            f.write(model_weights)

        print('Saved weights to local file')

        # Dynamically recreate the model class
        downloaded_namespace = {}
        exec(model_source_code, downloaded_namespace)

        # Identify the model class in the downloaded namespace
        downloaded_model_class = None
        for obj_name, obj in downloaded_namespace.items():
            if isinstance(obj, type) and issubclass(obj, torch.nn.Module) and obj != torch.nn.Module:
                downloaded_model_class = obj
                break

        if downloaded_model_class is None:
            print("No PyTorch model class found in the downloaded source code.")
        
            print("Creating nn.Sequential version...")

            # set up fields necessary for get_model_config

            fl_model = PytorchFLModel(
                model_name="Pytorch_NN",
                model_spec=model_specs
            )
        else:
            print("Recreated model class:", downloaded_model_class)

            # Reinitialize the PytorchFLModel and load the weights
            fl_model = PytorchFLModel(
                model_name="Pytorch_NN",
                pytorch_module=downloaded_model_class,
                module_init_params=init_params,
            )
        
            fl_model.load_model(
                pytorch_module=downloaded_model_class,
                model_filename=downloaded_weights_path,
                module_init_params=init_params,
            )

        print("PytorchFLModel successfully reconstructed and loaded.")
        return fl_model


    def load_firebase_datahandler(self, firebase_datahandler_path):

        # get datahandler data from firebase
        firebase_datahandler_ref = db.reference(firebase_datahandler_path)
        datahandler_data = firebase_datahandler_ref.get()
        if datahandler_data is None:
            print("Error: No DataHandler data found in Firebase.")
            return
        
        print('Datahandler data acquired from firebase')

        # decode the source code and configuration
        datahandler_source_code = decode_from_base64(datahandler_data["source_code"]).decode("utf-8")
        data_config = eval(decode_from_base64(datahandler_data["data_config"]).decode("utf-8"))

        # dynamically recreate the DataHandler class
        namespace = {}
        exec(datahandler_source_code, namespace)

        # find the datahandler class, which must be a subclass of DataHandler
        datahandler_class = None
        for obj_name, obj in namespace.items():
            if isinstance(obj, type) and issubclass(obj, namespace.get('DataHandler', object)) and obj != namespace['DataHandler']:
                datahandler_class = obj
                break

        if datahandler_class is None:
            raise ValueError("No DataHandler subclass found in the downloaded source code.")
        else:
            print("Recreated DataHandler class:", datahandler_class)

        # data config contains the data paths for all nodes
        # usually, i think it'd make more sense for the nodes to set this in their local .env files
        # but for now, data config contains all paths-- we can access this specific node's from the replica name
        replicaNumber = int(self.replicaName[-1])
        key = next(iter(data_config))
        personal_data_config = {key: data_config[key][replicaNumber]}


        # initialize the datahandler with the configuration
        data_handler = datahandler_class(data_config=personal_data_config)
        print("DataHandler successfully reconstructed and initialized.")
        return data_handler
            
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
            external_ip = os.getenv("EXTERNAL_IP")
            url = f'http://{external_ip}:32049'

            headers = {
                'User-Agent': 'AnyLog/1.23',
                'Content-Type': 'text/plain',
                'command': 'blockchain insert where policy = !my_policy and local = true and blockchain = optimism'
            }

            # denote node's parameters on blockchain with r
            data = f'''<my_policy = {{"r{round_number}" : {{
                    "node" : "{self.replicaName}",
                    "trained_params": "{newly_trained_params_db_link}"
            }} }}>'''

            # retries = 0;
            # max_retries = 5;
            # while retries < max_retries:
            #     response = requests.post(url, headers=headers, data=data)
            #     if response.status_code == 200:
            #         print(f"{self.replicaName} has submitted results for round {round_number}")
            #         return {
            #             'status': 'success',
            #             'message': 'node model parameters added successfully'
            #         }
            #     else:
            #         print(f"Failed to add node {self.replicaName} params to blockchain. Response: {response}. Retrying ({retries + 1}/{max_retries})...")
            #         retries += 1;
            #         time.sleep(15);
            
            # return {
            #             'status': 'error',
            #             'message': 'node was unable to add to blockchain'
            #         }

            response = requests.post(url, headers=headers, data=data)
            print("response after addding node data to blockchain ", response);

            print(f"{self.replicaName} has submitted results for round {round_number}")

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
        print(f"Training for round {round_number}")
        
        weights = ''

        # First round initialization
        if round_number == 1:
            #print('initializing weights, round1')
            weights = self.local_training_handler.fl_model.get_model_update()
            #print("round 1 weights", weights)
        else:
            try:
                #print('round1+, getting weights from aggregator')
                # Extract the key from the URL
                model_updates_key = aggregator_model_params_db_link.split('/')[-1].replace('.json', '')

                # Reference the database path and retrieve the data
                agg_data_ref = db.reference(f'agg_model_updates/{model_updates_key}')
                data = agg_data_ref.get()

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
        data_pushed = db.reference('node_model_updates').push({
            'replicaName': self.replicaName,
            'model_update': encoded_params
        })

        print('Pushed weights to Firebase')

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

    
    # modified to get test data from datahandler
    def inference(self, data):
        data1 = self.data_handler.get_data()
        print("got data from inference handler")
        data_test = data1[1];
        results = self.fl_model.evaluate(data_test)
        print("results ", results);
        return results
