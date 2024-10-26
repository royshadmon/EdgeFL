import os
import json
from web3 import Web3
from ibmfl.party.training.local_training_handler import LocalTrainingHandler

class Node:
    def __init__(self, contract_address, provider_url, private_key, config):

        # Initialize Web3 connection to the Ethereum node
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
    
        self.contract_address = contract_address

        # Set the deployer's private key and address
        self.private_key = private_key
        self.node_account = self.w3.eth.account.privateKeyToAccount(private_key)
        self.node_address = self.node_account.address

        # Load the ABI
        base_path = os.path.join(os.path.dirname(__file__), 'smart-contract')
        with open(os.path.join(base_path, 'ModelParametersABI.json'), 'r') as abi_file:
            self.contract_abi = json.load(abi_file)

        self.contract_instance = w3.eth.contract(address = self.contract_address, abi = self.contract_abi)

        # Node local data batches
        self.data_batches = []
        
        # IBM FL LocalTrainingHandler
        self.config = config
        fl_model = config['model']['path']
        data_handler = config['data']['path'] 
        self.local_training_handler = LocalTrainingHandler(fl_model=fl_model, data_handler=data_handler)

    
    def add_data_batch(self, data):
        self.data_batches.append(data)

    def add_node_params(self, new_node_model_params):
        if not self.contract_instance:
            return {
                'status': 'error',
                'message': 'Contract not found'
            }

        try:
            # Build the transaction to call addNodeParams 
            tx = self.deployed_contract.functions.addNodeParams(new_node_model_params).buildTransaction({
                'from': self.node_address,
                'nonce': self.w3.eth.get_transaction_count(self.node_address),
                'gas': 100000,
                'gasPrice': self.w3.toWei('50', 'gwei')
            })

            # Sign and send the transaction for production environment
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

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
        - Returns new node model params
    '''
    def train_model_params(self, aggregator_model_params):
        # Get local Data
        if not self.local_training_handler.data_batches:
            return jsonify({"error": "No data to train on"}), 400
        
        data = self.local_training_handler.data_batches.pop(0)

        # Update local model with sent model params
        self.local_training_handler.model_update(aggregator_model_params)

        # Load local data
        self.local_training_handler.data_handler.load_data(data)

        # Do local training
        model_update = self.local_training_handler.train()

        # Return updated model parameters
        return jsonify({"status": "training_complete", "model_update": str(model_update)})


        