# EdgeLake Project

<!-- To Do

- Need to add different commands for Mac & Windows
  -->

## Why EdgeLake:

 **Efficiency:**  Reduces data transfer by sharing model parameters instead of sharing entire datasets.

- **Performance:** Our distributed system enables high-computation training to be split across multiple nodes, significantly enhancing speed and scalability compared to single-node processing. .

- **Privacy:** Keeps data on nodes, minimizing exposure risks and enhancing security with privacy-preserving technologies such as blockchain.


<!-- ## Prerequisites -->
<!-- we need specify more stuff here -->
### Software Requirements
- Python 3.9+ installed.
## Install ibmfl from the repo (does not work on python3.12)
 pip install "federated_learning_lib-2.0.1-py3-none-any.whl[pytorch]"
## MongoDB (for file handling)
### Install / setup
```bash
brew tap mongodb/brew  
brew install mongodb-community # requires Xcode 16.0+
brew install mongosh # (Optional) allows access through mongo-cli
sudo mkdir -p /usr/local/bin/mongodb/var/mongodb
sudo mkdir -p /usr/local/bin/mongodb/log/mongodb
sudo chown $USER /usr/local/bin/mongodb/
sudo chown $USER /usr/local/bin/mongodb/log/mongodb
```
[Mongo information](https://www.prisma.io/dataguide/mongodb/connecting-to-mongodb)
[Mongo Install](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/)
[Mongo Shell](https://www.mongodb.com/docs/mongodb-shell/)
### Start
```bash
brew services start mongodb-community
mongod --dbpath /usr/local/bin/mongodb/var/mongodb --logpath /usr/local/bin/mongodb/log/mongodb/mongo.log
```
# AnyLog-Edgelake Setup Guide

This guide will walk you through setting up and running the AnyLog-Edgelake system.

## Prerequisites

- Git
- Python (with pip)
- Ability to run shell scripts
- cURL (for API requests)

## Installation Steps

1. Clone the repository and switch to the merge branch:
   ```bash
   git clone https://github.com/isba1/Anylog-Edgelake-CSE115D.git
   cd Anylog-Edgelake-CSE115D
   git checkout merge-branch
   ```

2. Configure Environment Variables:
   - Navigate to `AnyLog/blockchain` directory
   - Locate the `.env` file
   - Modify the file with your required variables

3. Set up the Database:
   - Navigate to `AnyLog/blockchain`
   - Run the database setup script:
     ```bash
     ./db_script
     ```

4. Install Dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Start the Servers:
   ```bash
   ./start_servers.sh
   ```

## System Initialization

After starting the servers, you need to initialize the nodes. Use the following curl command:

To train on 1 node
```bash
curl -X POST http://localhost:8080/init \          
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [    
    "http://localhost:8081"
  ],
  "model_def": 1
}'
```
To train on 2 nodes
```bash
curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [    
    "http://localhost:8081", 
    "http://localhost:8082"
  ],
  "model_def": 1
}'
```
## Model definitions
To train on the MNIST dataset, set "model_def: 1"
To train on the Winniio dataset, set "model_def: 2"

Note that you need to also update the `blockchain/env_files/mnist.env` or `blockchain/env_files/winniio.env` files + initialize them before starting the node/aggregator server.

## Custom Data Handler
Documentation for creating custom data handler (needs to be finished).
Examples of working data handlers can be found in the directory `blockchain/data_handlers` 


## Starting the Training Process

To begin the training process for the MNIST Dataset, use this curl command:

```bash
curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5,
  "minParams": 1
}'
```

## Running inference once the model is trained
```
curl -X POST http://localhost:8081/inference
```

## Shutting Down the Servers

When you're done, you can stop all running servers using:
```bash
./kill_servers.sh
```

## Parameters Explained

### Initialization Parameters
- `nodeUrls`: Array of URLs for the participating nodes
- `model_def`: Model definition parameter (default: 1)

### Training Parameters
- `totalRounds`: Number of training rounds to perform
- `minParams`: Minimum number of parameters required (default: 1)

## Troubleshooting

If you encounter any issues:
1. Ensure all servers are running properly
2. Check that the `.env` file is configured correctly
3. Verify all ports (8080, 8081, 8082) are available
4. Make sure all prerequisites are installed
5. If servers aren't responding, try killing them with `./kill_servers.sh` and restart
