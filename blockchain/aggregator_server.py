from flask import Flask, jsonify, request
from aggregator import Aggregator
import threading
import time
import requests
import os
from web3 import HTTPProvider, Web3

app = Flask(__name__)

# model parameters abi (specifies contract's functions, events, & how to call them)
abi = [  {   "anonymous": False,   "inputs": [ {  "indexed": False,  "internalType": "uint256",  "name": "roundNumber",  "type": "uint256" }, {  "indexed": False,  "internalType": "string",  "name": "initParams",  "type": "string" }   ],   "name": "newRound",   "type": "event"  },  {   "anonymous": False,   "inputs": [ {  "indexed": False,  "internalType": "uint256",  "name": "numberOfParams",  "type": "uint256" }, {  "indexed": False,  "internalType": "string[]",  "name": "paramsFromNodes",  "type": "string[]" }   ],   "name": "updateAggregatorWithParamsFromNodes",   "type": "event"  },  {   "inputs": [ {  "internalType": "uint256",  "name": "roundNumber",  "type": "uint256" }, {  "internalType": "string",  "name": "newNodeParams",  "type": "string" }, {  "internalType": "string",  "name": "replicaName",  "type": "string" }   ],   "name": "addNodeParams",   "outputs": [],   "stateMutability": "nonpayable",   "type": "function"  },  {   "inputs": [ {  "internalType": "string",  "name": "initParams",  "type": "string" }, {  "internalType": "uint256",  "name": "roundNumber",  "type": "uint256" }, {  "internalType": "uint256",  "name": "minNumParams",  "type": "uint256" }   ],   "name": "startRound",   "outputs": [],   "stateMutability": "nonpayable",   "type": "function"  } ]
# ModelParameters.sol compiled bytecode 
bin = "60806040525f6001553480156012575f80fd5b50610bd7806100205f395ff3fe608060405234801561000f575f80fd5b5060043610610034575f3560e01c8063988b8eea14610038578063eabde83e14610054575b5f80fd5b610052600480360381019061004d9190610480565b610070565b005b61006e600480360381019061006991906104ec565b61014e565b005b816001805461007f91906105a1565b146100bf576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016100b69061062e565b60405180910390fd5b6001805f8282546100d091906105a1565b92505081905550825f808481526020019081526020015f2060010190816100f79190610850565b50805f808481526020019081526020015f20600401819055507f163e8ade3221dbd53087718ca76656187ecaefe47921c7f4626b2b745382ec6a8284604051610141929190610974565b60405180910390a1505050565b8260015414610192576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016101899061062e565b60405180910390fd5b5f808481526020019081526020015f205f0182908060018154018082558091505060019003905f5260205f20015f9091909190915090816101d39190610850565b505f808481526020019081526020015f2060030181908060018154018082558091505060019003905f5260205f20015f9091909190915090816102169190610850565b5060015f808581526020019081526020015f205f018054905061023991906109a2565b5f808581526020019081526020015f206002018260405161025a9190610a0f565b9081526020016040518091039020819055505f808481526020019081526020015f20600401545f808581526020019081526020015f205f0180549050036102fb577f16e7f36d0f98350b33fa4a6a3e06110ae9b53109b25bdebcbdd3d8c7117025515f808581526020019081526020015f205f01805490505f808681526020019081526020015f205f016040516102f2929190610b73565b60405180910390a15b505050565b5f604051905090565b5f80fd5b5f80fd5b5f80fd5b5f80fd5b5f601f19601f8301169050919050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52604160045260245ffd5b61035f82610319565b810181811067ffffffffffffffff8211171561037e5761037d610329565b5b80604052505050565b5f610390610300565b905061039c8282610356565b919050565b5f67ffffffffffffffff8211156103bb576103ba610329565b5b6103c482610319565b9050602081019050919050565b828183375f83830152505050565b5f6103f16103ec846103a1565b610387565b90508281526020810184848401111561040d5761040c610315565b5b6104188482856103d1565b509392505050565b5f82601f83011261043457610433610311565b5b81356104448482602086016103df565b91505092915050565b5f819050919050565b61045f8161044d565b8114610469575f80fd5b50565b5f8135905061047a81610456565b92915050565b5f805f6060848603121561049757610496610309565b5b5f84013567ffffffffffffffff8111156104b4576104b361030d565b5b6104c086828701610420565b93505060206104d18682870161046c565b92505060406104e28682870161046c565b9150509250925092565b5f805f6060848603121561050357610502610309565b5b5f6105108682870161046c565b935050602084013567ffffffffffffffff8111156105315761053061030d565b5b61053d86828701610420565b925050604084013567ffffffffffffffff81111561055e5761055d61030d565b5b61056a86828701610420565b9150509250925092565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52601160045260245ffd5b5f6105ab8261044d565b91506105b68361044d565b92508282019050808211156105ce576105cd610574565b5b92915050565b5f82825260208201905092915050565b7f496e636f727265637420726f756e64206e756d626572000000000000000000005f82015250565b5f6106186016836105d4565b9150610623826105e4565b602082019050919050565b5f6020820190508181035f8301526106458161060c565b9050919050565b5f81519050919050565b7f4e487b71000000000000000000000000000000000000000000000000000000005f52602260045260245ffd5b5f600282049050600182168061069a57607f821691505b6020821081036106ad576106ac610656565b5b50919050565b5f819050815f5260205f209050919050565b5f6020601f8301049050919050565b5f82821b905092915050565b5f6008830261070f7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff826106d4565b61071986836106d4565b95508019841693508086168417925050509392505050565b5f819050919050565b5f61075461074f61074a8461044d565b610731565b61044d565b9050919050565b5f819050919050565b61076d8361073a565b6107816107798261075b565b8484546106e0565b825550505050565b5f90565b610795610789565b6107a0818484610764565b505050565b5b818110156107c3576107b85f8261078d565b6001810190506107a6565b5050565b601f821115610808576107d9816106b3565b6107e2846106c5565b810160208510156107f1578190505b6108056107fd856106c5565b8301826107a5565b50505b505050565b5f82821c905092915050565b5f6108285f198460080261080d565b1980831691505092915050565b5f6108408383610819565b9150826002028217905092915050565b6108598261064c565b67ffffffffffffffff81111561087257610871610329565b5b61087c8254610683565b6108878282856107c7565b5f60209050601f8311600181146108b8575f84156108a6578287015190505b6108b08582610835565b865550610917565b601f1984166108c6866106b3565b5f5b828110156108ed578489015182556001820191506020850194506020810190506108c8565b8683101561090a5784890151610906601f891682610819565b8355505b6001600288020188555050505b505050505050565b6109288161044d565b82525050565b8281835e5f83830152505050565b5f6109468261064c565b61095081856105d4565b935061096081856020860161092e565b61096981610319565b840191505092915050565b5f6040820190506109875f83018561091f565b8181036020830152610999818461093c565b90509392505050565b5f6109ac8261044d565b91506109b78361044d565b92508282039050818111156109cf576109ce610574565b5b92915050565b5f81905092915050565b5f6109e98261064c565b6109f381856109d5565b9350610a0381856020860161092e565b80840191505092915050565b5f610a1a82846109df565b915081905092915050565b5f81549050919050565b5f82825260208201905092915050565b5f819050815f5260205f209050919050565b5f82825260208201905092915050565b5f8154610a6d81610683565b610a778186610a51565b9450600182165f8114610a915760018114610aa757610ad9565b60ff198316865281151560200286019350610ad9565b610ab0856106b3565b5f5b83811015610ad157815481890152600182019150602081019050610ab2565b808801955050505b50505092915050565b5f610aed8383610a61565b905092915050565b5f600182019050919050565b5f610b0b82610a25565b610b158185610a2f565b935083602082028501610b2785610a3f565b805f5b85811015610b6157848403895281610b428582610ae2565b9450610b4d83610af5565b925060208a01995050600181019050610b2a565b50829750879550505050505092915050565b5f604082019050610b865f83018561091f565b8181036020830152610b988184610b01565b9050939250505056fea264697066735822122083523fd9e7036bb40374abb31e99aa1e3954a6d4598dc5e5150d0a4bdcd9595464736f6c634300081a0033"


# Use environment variables for sensitive data
# PROVIDER_URL = os.getenv('PROVIDER_URL', 'https://optimism-sepolia.infura.io/v3/524787abec0740b9a443cb825966c31e')
# PRIVATE_KEY = os.getenv('PRIVATE_KEY', 'f155acda1fc73fa6f50456545e3487b78fd517411708ffa1f67358c1d3d54977')
PROVIDER_URL = 'https://optimism-sepolia.infura.io/v3/524787abec0740b9a443cb825966c31e'
PRIVATE_KEY = 'f155acda1fc73fa6f50456545e3487b78fd517411708ffa1f67358c1d3d54977'
PUBLIC_KEY = "0x5F02C14eDd7491e339bDf4e942b228A688515838" # use for node addresses 
# Connect to provider
                                                               # camille's api key
w3 = Web3(HTTPProvider("https://optimism-sepolia.infura.io/v3/524787abec0740b9a443cb825966c31e"))
print (f"IS CONNECTED {w3.is_connected()}")

senderAccount = w3.eth.account.from_key(PRIVATE_KEY)

# Initialize the Aggregator instance
aggregator = Aggregator(PROVIDER_URL, PRIVATE_KEY)

'''
CURL REQUEST FOR DEPLOYING CONTRACT

curl -X POST http://localhost:8080/deploy-contract \
-H "Content-Type: application/json" \
-d '{
  "nodeAddresses": [
    "0x5F02C14eDd7491e339bDf4e942b228A688515838"
  ],
  "nodeUrls": [
    "http://localhost:8081"
  ],
  "config": {  
    "model": {
      "path": "/path/to/model"
    },
    "data": {
      "path": "/path/to/data"
    }
  }
}'
'''

@app.route('/deploy-contract', methods=['POST'])
def deploy_contract():
    """Deploy the smart contract with predefined nodes."""
    try:
        data = request.json
        node_addresses = data.get('nodeAddresses', [])
        node_urls = data.get('nodeUrls', [])
        config = data.get('config', {})
        batch_size = data.get('batch_size', 32)

        if not node_addresses:
            return jsonify({'status': 'error', 'message': 'No nodes provided'}), 400

        # Deploy the contract and return the result
        result = aggregator.deploy_contract()
        if result['status'] == 'success':
            contract_address = result['contractAddress']
            print(f"Contract deployed at address: {contract_address}")

            # Send the contract address to each node
            initialize_nodes(contract_address, node_urls, config)

            # initialize sql
            sql_setup(len(node_urls))

            # start data source
            initialize_data_source(node_urls, batch_size)

        return jsonify(result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def initialize_nodes(contract_address, node_urls, config):
    """Send the deployed contract address to multiple node servers."""
    for url in node_urls:
        try:
            response = requests.post(f'{url}/init-node', json={
                'contractAddress': contract_address,
                'config': config
            })
            if response.status_code == 200:
                print(f"Contract address successfully sent to node at {url}")
            else:
                print(f"Failed to send contract address to {url}: {response.text}")
        except Exception as e:
            print(f"Error sending contract address to {url}: {str(e)}")

def initialize_data_source(node_urls, batch_size=32):
    """Initialize the data source with node URLs and batch size."""
    try:
        # Send request to data_source_server's /init endpoint
        response = requests.post(
            'http://localhost:5002/init',  # URL for data_source_server's /init
            json={
                'node_urls': node_urls,
                'batch_size': batch_size
            }
        )
        # Check if the initialization was successful
        if response.status_code == 200:
            print("Data source successfully initialized.")
            return {
                'status': 'success',
                'message': response.json().get('message', 'Data source initialized')
            }
        else:
            print(f"Failed to initialize data source: {response.text}")
            return {
                'status': 'error',
                'message': response.text
            }
        
    except Exception as e:
        error_message = f"Error initializing data source: {str(e)}"
        print(error_message)
        return {
            'status': 'error',
            'message': error_message
        }
    
def sql_setup(num_nodes):
    response = requests.post(
        'http://localhost:5000/initialize', 
        json={'num_nodes': num_nodes} 
    )
    print("Initialize response:", response.json())
    if response.status_code == 201:
        print("Database and tables initialized successfully.")
    else:
        print("Error initializing database:", response.json())


'''
EXAMPLE CURL REQUEST FOR STARTING TRAINING

curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5, 
  "minParams": 1
}'
'''

@app.route('/start-training', methods=['POST'])
async def init_training():
    """Start the training process by setting the number of rounds."""
    try:
        data = request.json
        num_rounds = data.get('totalRounds', 1)
        min_params = data.get('minParams', 1)

        if num_rounds <= 0:
            return jsonify({'status': 'error', 'message': 'Invalid number of rounds'}), 400

        print(f"Training initialized with {num_rounds} rounds.")

        initialParams = ''

        for r in range(1, num_rounds + 1):
            print(f"Starting round {r}")
            aggregator.start_round(initialParams, r, min_params)

            # Listen for updates from nodes
            newAggregatorParams = await listen_for_update_agg()
            print("Received aggregated parameters")

            # Set initial params to newly aggregated params for the next round
            initialParams = newAggregatorParams

        return jsonify({'status': 'success', 'message': 'Training completed successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


async def listen_for_update_agg():
    """Asynchronously poll for the 'updateAggregatorWithParamsFromNodes' event from the blockchain."""
    print("Starting async polling for 'updateAggregatorWithParamsFromNodes' events...")

    # Define the event signature for 'updateAggregatorWithParamsFromNodes(uint256,string[])' and ensure it starts with '0x'
    event_signature = "0x" + aggregator.w3.keccak(text="updateAggregatorWithParamsFromNodes(uint256,string[])").hex()

    lastest_block = aggregator.w3.eth.block_number

    while True:
        try:
            # Define filter parameters for polling
            filter_params = {
                "fromBlock": lastest_block + 1,
                "toBlock": "latest",
                "address": aggregator.deployed_contract_address,
                "topics": [event_signature]
            }

            # Poll for logs
            logs = aggregator.w3.eth.get_logs(filter_params)
            for log in logs:
                # Decode event data
                decoded_event = aggregator.deployed_contract.events.updateAggregatorWithParamsFromNodes.process_log(log)
                number_of_params = decoded_event['args']['numberOfParams']
                params_from_nodes = decoded_event['args']['paramsFromNodes']

                print(f"Received 'updateAgg' event with params: {params_from_nodes}. Number of params: {number_of_params}")

                # Aggregate parameters
                newAggregatorParams = aggregator.aggregate_model_params(params_from_nodes)

                # Return the updated aggregator parameters and exit the function
                return newAggregatorParams

            # Update latest_block to avoid re-processing old events
            if logs:
                latest_block = logs[-1]['blockNumber']

        except Exception as e:
            print(f"Error polling for 'updateAgg' event: {str(e)}")

        # Asynchronously sleep to avoid excessive polling
        time.sleep(2)  # Poll every 2 seconds


if __name__ == '__main__':
    # Run the Flask server
    app.run(host='0.0.0.0', port=8080)