import os
import json
import numpy as np
from web3 import Web3
from ibmfl.party.training.local_training_handler import LocalTrainingHandler


class Node:
    def __init__(self, contract_address, provider_url, private_key, config, replica_name):

        # Initialize Web3 connection to the Ethereum node
        self.w3 = Web3(Web3.HTTPProvider(provider_url))

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
        fl_model = config['model']['path']
        data_handler = config['data']['path']
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
            tx = self.contract_instance.functions.addNodeParams(round_number, newly_trained_params, self.replicaName).build_transaction({
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

        startingTestArray = {}
        dataTestArray = np.zeros((1, 5))

        # Update local model with sent model params
        self.local_training_handler.update_model(startingTestArray)

        # Load local data
        self.local_training_handler.data_handler.load_data(dataTestArray)

        # Do local training
        model_update = self.local_training_handler.train()
        print(model_update) # see what is in the model update object

        # the node parameters part of model_update needs to be encoded to a string before being returned
        encoded_params = self.encode_params(model_update) # this will probably need to change to the correct field in model_update object

        return encoded_params

    def encode_params(self, model_params_as_numerical):
        # TO_DO encode the trained params as a string which is what the blockchain uses
        pass

    def decode_params(self, model_params_as_string):
        # TO_DO decode the model params from string format into numerical format to be used for training
        pass


