import os
import json
from web3 import Web3

class Node:
    def __init__(self, contract_address, provider_url, private_key):

        # Initialize Web3 connection to the Ethereum node
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
    
        self.contract_address = contract_address

        # Set the node's private key and address
        self.private_key = private_key
        self.node_account = self.w3.eth.account.privateKeyToAccount(private_key)
        self.node_address = self.node_account.address

        # Load the ABI
        base_path = os.path.join(os.path.dirname(__file__), 'smart-contract')
        with open(os.path.join(base_path, 'ModelParametersABI.json'), 'r') as abi_file:
            self.contract_abi = json.load(abi_file)

        self.contract_instance = w3.eth.contract(address = self.contract_address, abi = self.contract_abi)

    def add_node_params(new_node_model_params):
        if not self.contrac_instance:
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

    def train_model_params(aggregator_model_params):
        #TO DO
        # fine tune the model params from the aggregator with node's data


        