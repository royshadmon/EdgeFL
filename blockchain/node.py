import base64
import os
import json
import pickle
import zlib

import msgpack
import numpy as np
from web3 import Web3
from ibmfl.party.training.local_training_handler import LocalTrainingHandler
from ibmfl.util.data_handlers.mnist_pytorch_data_handler import MnistPytorchDataHandler
from ibmfl.model.pytorch_fl_model import PytorchFLModel


class Node:
    def __init__(self, contract_address, provider_url, private_key, config, replica_name):

        # Initialize Web3 connection to the Ethereum node
        self.w3 = Web3(Web3.HTTPProvider(provider_url, {"timeout": 100000}))


        self.replicaName = replica_name

        self.contract_address = contract_address

        # Set the node's private key and address
        self.private_key = private_key
        self.node_account = self.w3.eth.account.from_key(private_key)
        self.node_address = self.w3.to_checksum_address(self.node_account.address)

        balance = self.w3.eth.get_balance(self.node_address)
        print(f"Deployer Address Balance: {self.w3.from_wei(balance, 'ether')} ETH")

        # Load the ABI
        base_path = os.path.join(os.path.dirname(__file__), 'smart_contract')
        with open(os.path.join(base_path, 'ModelParametersABI.json'), 'r') as abi_file:
            self.contract_abi = json.load(abi_file)

        self.contract_instance = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)

        # Node local data batches
        self.data_batches = []

        # IBM FL LocalTrainingHandler
        self.config = config

        # USE MNIST DATASET FOR TESTING THIS FUNCTIONALITY
        # hard code for now for testing
        model_spec = {
            "loss_criterion": "nn.NLLLoss",
            "model_definition": "/Users/ishaandas/Documents/CSE_115D/Anylog-Edgelake-CSE115D/federated-learning-lib-main/examples/configs/iter_avg/pytorch/pytorch_sequence.pt",
            "model_name": "pytorch-nn",
            "optimizer": "optim.Adadelta"
        }
        data_config = {
            "npz_file": "/Users/ishaandas/Documents/CSE_115D/Anylog-Edgelake-CSE115D/blockchain/data/mnist/data_party0.npz"
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

    def add_node_params(self, round_number, newly_trained_params):
        if not self.contract_instance:
            return {
                'status': 'error',
                'message': 'Contract not found'
            }

        try:
            # Build the transaction to call addNodeParams 
            # new_node_model_params = self.local_training_handler.fl_model  # I think this would get the fl_model?
            tx = self.contract_instance.functions.addNodeParams(round_number, newly_trained_params,
                                                                self.replicaName).build_transaction({
                'from': self.node_address,
                'nonce': self.w3.eth.get_transaction_count(self.node_address),
                'chainId': 11155420
            })

            # Sign and send the transaction for production environment
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait for the transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                'status': 'success',
                'message': 'node model parameters added successfully',
                'transactionHash': tx_hash.hex()
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

    def train_model_params(self, aggregator_model_params):
        # Get local Data
        # if not self.data_batches:
        #     return jsonify({"error": "No data to train on"}), 400
        #
        # data = self.data_batches.pop(0)
        #
        # # decode model params from string to numerical
        # decoded_params = self.decode_params(aggregator_model_params)

        test_model_update = self.local_training_handler.fl_model.get_model_update()

        # Update local model with sent model params
        self.local_training_handler.update_model(test_model_update)

        # Load local data
        self.local_training_handler.data_handler.load_dataset(nb_points=50)

        # Do local training
        model_update = self.local_training_handler.train({})

        # the node parameters part of model_update needs to be encoded to a string before being returned
        encoded_params = self.encode_model(model_update)

        return encoded_params

    def encode_model(self, model_update):
        serialized_data = pickle.dumps(model_update)
        compressed_data = zlib.compress(serialized_data)
        encoded_model_update = base64.b64encode(compressed_data).decode('utf-8')
        return encoded_model_update

    def decode_params(self, encoded_model_update):
        # turns model params encoded string from nodes into decoded dict
        decoded_model_update = pickle.loads(encoded_model_update)
        return decoded_model_update
