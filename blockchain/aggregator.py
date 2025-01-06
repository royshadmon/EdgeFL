import base64
import os
from asyncio import sleep
import ast
from asyncore import write

import requests
import pickle
import zlib
from dotenv import load_dotenv
from pymongo import MongoClient

from web3 import Web3
from ibmfl.aggregator.fusion.iter_avg_fusion_handler import IterAvgFusionHandler
import firebase_admin
from firebase_admin import credentials, db
from ibmfl.model.model_update import ModelUpdate
from ibmfl.util.data_handlers.mnist_pytorch_data_handler import MnistPytorchDataHandler

from blockchain.blockchain_EL_functions import insert_policy
from blockchain.mongo_file_store import read_file, write_file

CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')

load_dotenv()


class Aggregator:
    def __init__(self, provider_url, private_key, ip, port):
        self.server_ip = ip
        self.server_port = port
        # Initialize Firebase database connection
        self.database_url = os.getenv('DATABASE_URL')

        cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS'))
        firebase_admin.initialize_app(cred, {
            'databaseURL': self.database_url
        })

        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        self.edgelake_tcp_node_ip_port = f'{os.getenv("EXTERNAL_TCP_IP_PORT")}'
        self.contract_address = self.get_contract_address()

        # Correctly instantiate the Fusion model here (using IterAvg as place holder for now)
        # Define or obtain hyperparameters and protocol handler for the fusion model
        hyperparams = {}  # Replace with actual hyperparameters as required
        protocol_handler = None  # Replace with an appropriate protocol handler instance or object

        # USE MNIST DATASET FOR TESTING THIS FUNCTIONALITY
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(current_dir, "mnist.npz")
        data_config = {
            "npz_file": str(data_path)
        }
        data_handler = MnistPytorchDataHandler(data_config=data_config)

        # Correctly instantiate the Fusion model with required arguments
        self.fusion_model = IterAvgFusionHandler(hyperparams, protocol_handler, data_handler=data_handler)

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
                elif response.status_code == 400:
                    if response.content.decode().__contains__("Duplicate blockchain object id"):
                        success = True
                else:
                    sleep(1)

            print(f"Training initialized with {roundNumber} rounds")

            # response = requests.post(self.edgelake_node_url, headers=headers, data=data)
            if response.status_code == 200:
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
        for i, link in enumerate(node_param_download_links):
            try:
                link = ast.literal_eval(link)
                # make sure directory exists
                os.makedirs(os.path.dirname(
                    f"/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/aggregator/"),
                            exist_ok=True)
                response = read_file(self.edgelake_node_url, link[0], link[1], link[2], f'/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/aggregator/{link[2]}', ip_ports[i])
                # response = requests.get(link)
                if response.status_code == 200:
                    sleep(1)
                    with open(f'/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/aggregator/{link[2]}', 'rb') as f:
                        data = pickle.load(f)

                    if not data:
                        raise ValueError(f"Missing model_weights in data from link: {link}")
                    decoded_params.append(data)
                else:
                    raise ValueError(
                        f"Failed to retrieve node params from link: {link}. HTTP Status: {response.status_code}")
            except Exception as e:
                raise ValueError(f"Error retrieving data from link {link}: {str(e)}")

        # do aggregation function here (doesn't return anything)
        self.fusion_model.update_weights(decoded_params)

        aggregate_params_weights = self.fusion_model.current_model_weights

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
        with open(f'/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/aggregator/{round_number}-agg_update.json', 'wb') as f:
            f.write(self.encode_params(data_entry))
        write_file(self.edgelake_node_url, 'blobs_admin', 'agg_model_updates', f'/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/aggregator/{round_number}-agg_update.json')
        # data_pushed = agg_ref.push(data_entry)

        # object_url = f"{self.database_url}/agg_model_updates/{data_pushed.key}.json"

        # clear the node model updates for clean slate during new round
        #node_ref.delete()
        return "blobs_admin", "agg_model_updates", f'{round_number}-agg_update.json'
        # return object_url

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
