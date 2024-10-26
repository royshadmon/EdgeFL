from aggregator import Aggregator

# this should be the flask server

# Initialize the AggregatorContract class with your node's provider URL and private key
aggregator = AggregatorContract(
    provider_url='http://127.0.0.1:8545',  # Local Ethereum node software
    private_key='<SOME-PRIVATE-KEY>'  # Replace with your private key from metemask wallet or Ethereum account
)

# Deploy the contract
deploy_result = aggregator.deploy_contract()
print(deploy_result)

# If the deployment was successful, call the initTraining function
if deploy_result['status'] == 'success':
    training_result = aggregator.init_training()
    print(training_result)
