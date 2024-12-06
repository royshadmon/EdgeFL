import base64
import os
import requests
import pickle
import zlib
from dotenv import load_dotenv

from web3 import Web3
from ibmfl.aggregator.fusion.iter_avg_fusion_handler import IterAvgFusionHandler
import firebase_admin
from firebase_admin import credentials, db
from ibmfl.model.model_update import ModelUpdate

import time

load_dotenv()


class Aggregator:
    def __init__(self, provider_url, private_key):
        # Initialize Firebase database connection
        self.database_url = os.getenv('DATABASE_URL')

        cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS'))
        firebase_admin.initialize_app(cred, {
            'databaseURL': self.database_url
        })

        # Load the ABI and bytecode

        # Correctly instantiate the Fusion model here (using IterAvg as place holder for now)
        # Define or obtain hyperparameters and protocol handler for the fusion model
        hyperparams = {}  # Replace with actual hyperparameters as required
        protocol_handler = None  # Replace with an appropriate protocol handler instance or object

        # Correctly instantiate the Fusion model with required arguments
        self.fusion_model = IterAvgFusionHandler(hyperparams, protocol_handler)

    # function to call the start round function from the smart contract
    def start_round(self, initParamsLink, roundNumber):
        try:
            # Build the complete URL with port
            external_ip = os.getenv("EXTERNAL_IP")
            url = f'http://{external_ip}:32049'

            # in khaled's: for node_num in range(1, int(minParams) + 1)
            headers = {
                'User-Agent': 'AnyLog/1.23',
                'Content-Type': 'text/plain',
                'command': 'blockchain insert where policy = !my_policy and local = true and blockchain = optimism'
            }

            # Format data exactly like the example curl command but with your values
            # denote aggregator's params with a 
            data = f'''<my_policy = {{"a{roundNumber}" : {{
                                        "initParams": "{initParamsLink}"
                              }} }}>'''

            # retries = 0;
            # max_retries = 5;
            # while retries < max_retries:
            #     response = requests.post(url, headers=headers, data=data)
            #     if response.status_code == 200:
            #         print(f"Aggregator has submitted parameters for round {roundNumber} to the blockchain.")
            #         return {
            #             'status': 'success',
            #             'message': 'Aggregator model parameters added successfully'
            #         }
            #     else:
            #         print(f"Failed to add aggregator params to blockchain. Response: {response}. Retrying ({retries + 1}/{max_retries})...")
            #         retries += 1;
            #         time.sleep(15);
        
            # return {
            #     'status': 'error',
            #     'message': 'aggregator was unable to add to blockchain'
            # }
            
            response = requests.post(url, headers=headers, data=data)
            print(response.status_code)
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

    def aggregate_model_params(self, node_param_download_links):
        node_ref = db.reference('node_model_updates')

        decoded_params = []
        # Loop through each provided download link to retrieve node parameter objects
        for link in node_param_download_links:
            try:
                response = requests.get(link)
                if response.status_code == 200:
                    data = response.json()
                    model_weights = data.get('model_update')
                    if not model_weights:
                        raise ValueError(f"Missing model_weights in data from link: {link}")
                    decoded_params.append(self.decode_params(model_weights))
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

        agg_ref = db.reference('agg_model_updates')

        # delete the old aggregated params
        if agg_ref.get() is not None:
            agg_ref.delete()

        data_entry = {
            'newUpdates': encoded_params
        }

        # push agg data
        data_pushed = agg_ref.push(data_entry)

        object_url = f"{self.database_url}/agg_model_updates/{data_pushed.key}.json"

        # clear the node model updates for clean slate during new round
        node_ref.delete()

        return object_url

    def encode_params(self, new_model_weights):
        serialized_data = pickle.dumps(new_model_weights)
        compressed_data = zlib.compress(serialized_data)
        encoded_model_update = base64.b64encode(compressed_data).decode('utf-8')
        return encoded_model_update

    def decode_params(self, encoded_model_update):
        compressed_data = base64.b64decode(encoded_model_update)
        serialized_data = zlib.decompress(compressed_data)
        model_weights = pickle.loads(serialized_data)
        return model_weights

    def inference(self, model, data):
        results = model.evaluate(data)
        return results