import os
import json
from web3 import Web3
from ibmfl.aggregator.fusion.iter_avg_fusion_handler import IterAvgFusionHandler

abi = [  {   "anonymous": False,   "inputs": [ {  "indexed": False,  "internalType": "uint256",  "name": "roundNumber",  "type": "uint256" }, {  "indexed": False,  "internalType": "string",  "name": "initParams",  "type": "string" }   ],   "name": "newRound",   "type": "event"  },  {   "anonymous": False,   "inputs": [ {  "indexed": False,  "internalType": "uint256",  "name": "numberOfParams",  "type": "uint256" }, {  "indexed": False,  "internalType": "string[]",  "name": "paramsFromNodes",  "type": "string[]" }   ],   "name": "updateAggregatorWithParamsFromNodes",   "type": "event"  },  {   "inputs": [ {  "internalType": "uint256",  "name": "roundNumber",  "type": "uint256" }, {  "internalType": "string",  "name": "newNodeParams",  "type": "string" }, {  "internalType": "string",  "name": "replicaName",  "type": "string" }   ],   "name": "addNodeParams",   "outputs": [],   "stateMutability": "nonpayable",   "type": "function"  },  {   "inputs": [ {  "internalType": "string",  "name": "initParams",  "type": "string" }, {  "internalType": "uint256",  "name": "roundNumber",  "type": "uint256" }, {  "internalType": "uint256",  "name": "minNumParams",  "type": "uint256" }   ],   "name": "startRound",   "outputs": [],   "stateMutability": "nonpayable",   "type": "function"  } ]
bin = "60806040525f6001553480156012575f80fd5b50610bd7806100205f395ff3fe608060405234801561000f575f80fd5b5060043610610034575f3560e01c8063988b8eea14610038578063eabde83e14610054575b5f80fd5b610052600480360381019061004d9190610480565b610070565b005b61006e600480360381019061006991906104ec565b61014e565b005b816001805461007f91906105a1565b146100bf576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016100b69061062e565b60405180910390fd5b6001805f8282546100d091906105a1565b92505081905550825f808481526020019081526020015f2060010190816100f79190610850565b50805f808481526020019081526020015f20600401819055507f163e8ade3221dbd53087718ca76656187ecaefe47921c7f4626b2b745382ec6a8284604051610141929190610974565b60405180910390a1505050565b8260015414610192576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016101899061062e565b60405180910390fd5b5f808481526020019081526020015f205f0182908060018154018082558091505060019003905f5260205f20015f9091909190915090816101d39190610850565b505f808481526020019081526020015f2060030181908060018154018082558091505060019003905f5260205f20015f9091909190915090816102169190610850565b5060015f808581526020019081526020015f205f018054905061023991906109a2565b5f808581526020019081526020015f206002018260405161025a9190610a0f565b9081526020016040518091039020819055505f808481526020019081526020015f20600401545f808581526020019081526020015f205f0180549050036102fb577f16e7f36d0f98350b33fa4a6a3e06110ae9b53109b25bdebcbdd3d8c7117025515f808581526020019081526020015f205f01805490505f808681526020019081526020015f205f016040516102f2929190610b73565b60405180910390a15b505050565b5f604051905090565b5f80fd5b5f80fd5b5f80fd5b5f80fd5b5f601f19601f8301169050919050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52604160045260245ffd5b61035f82610319565b810181811067ffffffffffffffff8211171561037e5761037d610329565b5b80604052505050565b5f610390610300565b905061039c8282610356565b919050565b5f67ffffffffffffffff8211156103bb576103ba610329565b5b6103c482610319565b9050602081019050919050565b828183375f83830152505050565b5f6103f16103ec846103a1565b610387565b90508281526020810184848401111561040d5761040c610315565b5b6104188482856103d1565b509392505050565b5f82601f83011261043457610433610311565b5b81356104448482602086016103df565b91505092915050565b5f819050919050565b61045f8161044d565b8114610469575f80fd5b50565b5f8135905061047a81610456565b92915050565b5f805f6060848603121561049757610496610309565b5b5f84013567ffffffffffffffff8111156104b4576104b361030d565b5b6104c086828701610420565b93505060206104d18682870161046c565b92505060406104e28682870161046c565b9150509250925092565b5f805f6060848603121561050357610502610309565b5b5f6105108682870161046c565b935050602084013567ffffffffffffffff8111156105315761053061030d565b5b61053d86828701610420565b925050604084013567ffffffffffffffff81111561055e5761055d61030d565b5b61056a86828701610420565b9150509250925092565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52601160045260245ffd5b5f6105ab8261044d565b91506105b68361044d565b92508282019050808211156105ce576105cd610574565b5b92915050565b5f82825260208201905092915050565b7f496e636f727265637420726f756e64206e756d626572000000000000000000005f82015250565b5f6106186016836105d4565b9150610623826105e4565b602082019050919050565b5f6020820190508181035f8301526106458161060c565b9050919050565b5f81519050919050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52602260045260245ffd5b5f600282049050600182168061069a57607f821691505b6020821081036106ad576106ac610656565b5b50919050565b5f819050815f5260205f209050919050565b5f6020601f8301049050919050565b5f82821b905092915050565b5f6008830261070f7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff826106d4565b61071986836106d4565b95508019841693508086168417925050509392505050565b5f819050919050565b5f61075461074f61074a8461044d565b610731565b61044d565b9050919050565b5f819050919050565b61076d8361073a565b6107816107798261075b565b8484546106e0565b825550505050565b5f90565b610795610789565b6107a0818484610764565b505050565b5b818110156107c3576107b85f8261078d565b6001810190506107a6565b5050565b601f821115610808576107d9816106b3565b6107e2846106c5565b810160208510156107f1578190505b6108056107fd856106c5565b8301826107a5565b50505b505050565b5f82821c905092915050565b5f6108285f198460080261080d565b1980831691505092915050565b5f6108408383610819565b9150826002028217905092915050565b6108598261064c565b67ffffffffffffffff81111561087257610871610329565b5b61087c8254610683565b6108878282856107c7565b5f60209050601f8311600181146108b8575f84156108a6578287015190505b6108b08582610835565b865550610917565b601f1984166108c6866106b3565b5f5b828110156108ed578489015182556001820191506020850194506020810190506108c8565b8683101561090a5784890151610906601f891682610819565b8355505b6001600288020188555050505b505050505050565b6109288161044d565b82525050565b8281835e5f83830152505050565b5f6109468261064c565b61095081856105d4565b935061096081856020860161092e565b61096981610319565b840191505092915050565b5f6040820190506109875f83018561091f565b8181036020830152610999818461093c565b90509392505050565b5f6109ac8261044d565b91506109b78361044d565b92508282039050818111156109cf576109ce610574565b5b92915050565b5f81905092915050565b5f6109e98261064c565b6109f381856109d5565b9350610a0381856020860161092e565b80840191505092915050565b5f610a1a82846109df565b915081905092915050565b5f81549050919050565b5f82825260208201905092915050565b5f819050815f5260205f209050919050565b5f82825260208201905092915050565b5f8154610a6d81610683565b610a778186610a51565b9450600182165f8114610a915760018114610aa757610ad9565b60ff198316865281151560200286019350610ad9565b610ab0856106b3565b5f5b83811015610ad157815481890152600182019150602081019050610ab2565b808801955050505b50505092915050565b5f610aed8383610a61565b905092915050565b5f600182019050919050565b5f610b0b82610a25565b610b158185610a2f565b935083602082028501610b2785610a3f565b805f5b85811015610b6157848403895281610b428582610ae2565b9450610b4d83610af5565b925060208a01995050600181019050610b2a565b50829750879550505050505092915050565b5f604082019050610b865f83018561091f565b8181036020830152610b988184610b01565b9050939250505056fea264697066735822122083523fd9e7036bb40374abb31e99aa1e3954a6d4598dc5e5150d0a4bdcd9595464736f6c634300081a0033"


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

    def decode_params(self, model_params_as_string):
        # TO_DO decode the model params from string format into numerical format to be used for training
        pass
