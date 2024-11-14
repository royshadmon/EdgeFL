import os
import json
import pickle

from web3 import Web3
from ibmfl.aggregator.fusion.iter_avg_fusion_handler import IterAvgFusionHandler

abi = [
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "roundNumber",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "initParams",
				"type": "string"
			}
		],
		"name": "newRound",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "numberOfNodes",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "replicaName",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "paramsFromNodes",
				"type": "string"
			}
		],
		"name": "updateAggregatorWithParamsFromNodes",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "roundNumber",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "newNodeParams",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "replicaName",
				"type": "string"
			},
			{
				"internalType": "bool",
				"name": "finishNode",
				"type": "bool"
			}
		],
		"name": "addNodeParams",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "initParams",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "roundNumber",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "minNumParams",
				"type": "uint256"
			}
		],
		"name": "startRound",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	}
]
bin = "60806040525f6001553480156012575f80fd5b50610d82806100205f395ff3fe608060405234801561000f575f80fd5b5060043610610034575f3560e01c8063107c884414610038578063988b8eea14610054575b5f80fd5b610052600480360381019061004d919061070f565b610070565b005b61006e600480360381019061006991906107ab565b61047d565b005b83600154146100b4576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016100ab90610871565b60405180910390fd5b5f808581526020019081526020015f20600101826040516100d591906108e1565b90815260200160405180910390205f0183908060018154018082558091505060019003905f5260205f20015f9091909190915090816101149190610af1565b5080156101e7575f808581526020019081526020015f206002018260405161013c91906108e1565b90815260200160405180910390205f9054906101000a900460ff166101e65760015f808681526020019081526020015f206002018360405161017e91906108e1565b90815260200160405180910390205f6101000a81548160ff0219169083151502179055505f808581526020019081526020015f2060030182908060018154018082558091505060019003905f5260205f20015f9091909190915090816101e49190610af1565b505b5b5f808581526020019081526020015f20600401545f808681526020019081526020015f206003018054905003610477575f5b5f808681526020019081526020015f2060030180549050811015610475575f805f8781526020019081526020015f20600301828154811061025d5761025c610bc0565b5b905f5260205f2001805461027090610924565b80601f016020809104026020016040519081016040528092919081815260200182805461029c90610924565b80156102e75780601f106102be576101008083540402835291602001916102e7565b820191905f5260205f20905b8154815290600101906020018083116102ca57829003601f168201915b505050505090505f5b5f808881526020019081526020015f206001018260405161031191906108e1565b90815260200160405180910390205f0180549050831015610466575f805f8981526020019081526020015f206001018360405161034e91906108e1565b90815260200160405180910390205f0182815481106103705761036f610bc0565b5b905f5260205f2001805461038390610924565b80601f01602080910402602001604051908101604052809291908181526020018280546103af90610924565b80156103fa5780601f106103d1576101008083540402835291602001916103fa565b820191905f5260205f20905b8154815290600101906020018083116103dd57829003601f168201915b505050505090507fcd2ef81da4dfcde2f0e280b5b9fb45203ed0ec0ca773854a95b1a79534528a015f808a81526020019081526020015f2060030180549050848360405161044a93929190610c34565b60405180910390a150808061045e90610ca4565b9150506102f0565b50508080600101915050610219565b505b50505050565b816001805461048c9190610ceb565b146104cc576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016104c390610871565b60405180910390fd5b6001805f8282546104dd9190610ceb565b92505081905550825f808481526020019081526020015f205f0190816105039190610af1565b50805f808481526020019081526020015f20600401819055507f163e8ade3221dbd53087718ca76656187ecaefe47921c7f4626b2b745382ec6a828460405161054d929190610d1e565b60405180910390a1505050565b5f604051905090565b5f80fd5b5f80fd5b5f819050919050565b61057d8161056b565b8114610587575f80fd5b50565b5f8135905061059881610574565b92915050565b5f80fd5b5f80fd5b5f601f19601f8301169050919050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52604160045260245ffd5b6105ec826105a6565b810181811067ffffffffffffffff8211171561060b5761060a6105b6565b5b80604052505050565b5f61061d61055a565b905061062982826105e3565b919050565b5f67ffffffffffffffff821115610648576106476105b6565b5b610651826105a6565b9050602081019050919050565b828183375f83830152505050565b5f61067e6106798461062e565b610614565b90508281526020810184848401111561069a576106996105a2565b5b6106a584828561065e565b509392505050565b5f82601f8301126106c1576106c061059e565b5b81356106d184826020860161066c565b91505092915050565b5f8115159050919050565b6106ee816106da565b81146106f8575f80fd5b50565b5f81359050610709816106e5565b92915050565b5f805f806080858703121561072757610726610563565b5b5f6107348782880161058a565b945050602085013567ffffffffffffffff81111561075557610754610567565b5b610761878288016106ad565b935050604085013567ffffffffffffffff81111561078257610781610567565b5b61078e878288016106ad565b925050606061079f878288016106fb565b91505092959194509250565b5f805f606084860312156107c2576107c1610563565b5b5f84013567ffffffffffffffff8111156107df576107de610567565b5b6107eb868287016106ad565b93505060206107fc8682870161058a565b925050604061080d8682870161058a565b9150509250925092565b5f82825260208201905092915050565b7f496e636f727265637420726f756e64206e756d626572000000000000000000005f82015250565b5f61085b601683610817565b915061086682610827565b602082019050919050565b5f6020820190508181035f8301526108888161084f565b9050919050565b5f81519050919050565b5f81905092915050565b8281835e5f83830152505050565b5f6108bb8261088f565b6108c58185610899565b93506108d58185602086016108a3565b80840191505092915050565b5f6108ec82846108b1565b915081905092915050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52602260045260245ffd5b5f600282049050600182168061093b57607f821691505b60208210810361094e5761094d6108f7565b5b50919050565b5f819050815f5260205f209050919050565b5f6020601f8301049050919050565b5f82821b905092915050565b5f600883026109b07fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff82610975565b6109ba8683610975565b95508019841693508086168417925050509392505050565b5f819050919050565b5f6109f56109f06109eb8461056b565b6109d2565b61056b565b9050919050565b5f819050919050565b610a0e836109db565b610a22610a1a826109fc565b848454610981565b825550505050565b5f90565b610a36610a2a565b610a41818484610a05565b505050565b5b81811015610a6457610a595f82610a2e565b600181019050610a47565b5050565b601f821115610aa957610a7a81610954565b610a8384610966565b81016020851015610a92578190505b610aa6610a9e85610966565b830182610a46565b50505b505050565b5f82821c905092915050565b5f610ac95f1984600802610aae565b1980831691505092915050565b5f610ae18383610aba565b9150826002028217905092915050565b610afa8261088f565b67ffffffffffffffff811115610b1357610b126105b6565b5b610b1d8254610924565b610b28828285610a68565b5f60209050601f831160018114610b59575f8415610b47578287015190505b610b518582610ad6565b865550610bb8565b601f198416610b6786610954565b5f5b82811015610b8e57848901518255600182019150602085019450602081019050610b69565b86831015610bab5784890151610ba7601f891682610aba565b8355505b6001600288020188555050505b505050505050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52603260045260245ffd5b610bf68161056b565b82525050565b5f610c068261088f565b610c108185610817565b9350610c208185602086016108a3565b610c29816105a6565b840191505092915050565b5f606082019050610c475f830186610bed565b8181036020830152610c598185610bfc565b90508181036040830152610c6d8184610bfc565b9050949350505050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52601160045260245ffd5b5f610cae8261056b565b91507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8203610ce057610cdf610c77565b5b600182019050919050565b5f610cf58261056b565b9150610d008361056b565b9250828201905080821115610d1857610d17610c77565b5b92915050565b5f604082019050610d315f830185610bed565b8181036020830152610d438184610bfc565b9050939250505056fea2646970667358221220802caedd47b56b78ac4b313985b1372d36fb9f40b6cf0b8393f567f630b781f664736f6c634300081a0033"
CONTRACT_ADDRESS = "0xF21E95f39Ac900986c4D47Bb17De767d80451e3B"

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
        self.contract_abi = abi
        self.contract_bytecode = bin

        # Correctly instantiate the Fusion model here (using IterAvg as place holder for now)
        # Define or obtain hyperparameters and protocol handler for the fusion model
        hyperparams = {}  # Replace with actual hyperparameters as required
        protocol_handler = None  # Replace with an appropriate protocol handler instance or object

        # Correctly instantiate the Fusion model with required arguments
        self.fusion_model = IterAvgFusionHandler(hyperparams, protocol_handler)

        # Store the deployed contract address
        self.deployed_contract_address = CONTRACT_ADDRESS
        self.deployed_contract = self.w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

    def deploy_contract(self):
        try:
            # Initialize the contract object
            contract = self.w3.eth.contract(abi=self.contract_abi, bytecode=self.contract_bytecode)

            # Build the deployment transaction
            tx = contract.constructor().build_transaction({
                'from': self.deployer_address,
                'nonce': self.w3.eth.get_transaction_count(self.deployer_address),
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
            print("before transaction")
            # Build the transaction to call initTraining
            tx = self.deployed_contract.functions.startRound(initParams, roundNumber, minParams).build_transaction({
                'from': self.deployer_address,
                'nonce': self.w3.eth.get_transaction_count(self.deployer_address),
                'chainId': 11155420
            })
            print("after transaction")

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

    def decode_params(self, encoded_model_update):
        # turns model params encoded string from nodes into decoded dict
        decoded_model_update_string = pickle.loads(encoded_model_update)
        decoded_model_update = decoded_model_update_string.decode('ascii')

        return decoded_model_update
