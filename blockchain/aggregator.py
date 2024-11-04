import os
import json
from web3 import Web3
from ibmfl.aggregator.fusion.iter_avg_fusion_handler import IterAvgFusionHandler


class Aggregator:
    def __init__(self, provider_url, private_key):
        # Initialize Web3 connection to the Ethereum node
        self.w3 = Web3(Web3.HTTPProvider(provider_url))

        # Check if the connection is successful
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to the Ethereum node")

        # Set the deployer's private key and address
        self.private_key = private_key
        self.deployer_account = self.w3.eth.account.from_key(private_key)
        self.deployer_address = self.w3.to_checksum_address(self.deployer_account.address)

        balance = self.w3.eth.get_balance(self.deployer_address)
        print(f"Deployer Address Balance: {self.w3.from_wei(balance, 'ether')} ETH")

        # Load the ABI and bytecode
        base_path = os.path.join(os.path.dirname(__file__), 'smart_contract')
        with open(os.path.join(base_path, 'ModelParametersABI.json'), 'r') as abi_file:
            self.contract_abi = json.load(abi_file)
        with open(os.path.join(base_path, 'ModelParametersBytecode.txt'), 'r') as bytecode_file:
            self.contract_bytecode = bytecode_file.read().strip()

        # Correctly instantiate the Fusion model here (using IterAvg as place holder for now)
        self.fusion_model = IterAvgFusionHandler()

        # Store the deployed contract address
        self.deployed_contract_address = None
        self.deployed_contract = None

    def deploy_contract(self):
        try:
            # Initialize the contract object
            contract = self.w3.eth.contract(abi=self.contract_abi, bytecode=self.contract_bytecode)

            # Build the deployment transaction
            tx = contract.constructor().build_transaction({
                'from': self.deployer_address,
                'nonce': self.w3.eth.get_transaction_count(self.deployer_address),
                'gas': 2000000,
                'gasPrice': self.w3.to_wei('50', 'gwei')
            })

            # Sign and send the transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait for the transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # save contract address and contract
            self.deployed_contract_address = receipt.contractAddress
            self.deployed_contract = self.w3.eth.contract(address=self.deployed_contract_address, abi=self.contract_abi)

            return {
                'status': 'success',
                'contractAddress': self.deployed_contract_address,
                'transactionHash': tx_hash.hex()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    # function to call the start round function from the smart contract
    def start_round(self, initParams, roundNumber, minParams):
        """Call the startRound function of the deployed contract."""
        if not self.deployed_contract_address:
            return {
                'status': 'error',
                'message': 'Contract not deployed yet'
            }

        try:

            # Build the transaction to call initTraining
            tx = self.deployed_contract.functions.startRound(initParams, roundNumber, minParams).build_transaction({
                'from': self.deployer_address,
                'nonce': self.w3.eth.get_transaction_count(self.deployer_address),
                'gas': 100000,
                'gasPrice': self.w3.toWei('50', 'gwei')
            })

            # Sign and send the transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait for the transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                'status': 'success',
                'message': 'initTraining called successfully',
                'transactionHash': tx_hash.hex()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def aggregate_model_params(self, model_params_from_nodes):
        # TO DO
        # aggregate model params from nodes using some fusion model like iter_avg etc.
        decoded_params = self.decode_params(model_params_from_nodes)

        # do aggregation function here
        aggregated_params = self.fusion_model.update_weights(decoded_params)

        # encode params back to string
        encoded_params = self.encode_params(aggregated_params)

        return encoded_params

    def encode_params(self, model_params_as_numerical):
        # TO_DO encode the trained params as a string which is what the blockchain uses
        pass

    def decode_params(self, model_params_as_string):
        # TO_DO decode the model params from string format into numerical format to be used for training
        pass
