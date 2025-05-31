# EdgeFL

## Overview

The following is instructions to simulate the continuous Federated Learning (FL) lifecycle 
consisting of three training nodes and one aggregator node. Each node will utilize its
own EdgeLake node, such that we will deploy four EdgeLake nodes, three of which have 
operator roles and one with the master role. The master role is a normal EdgeLake operator
node but also emulates the same blockchain-like functionality of the blockchain-back shared
metadata layer. For more infomation about EdgeLake and how it operates, check the [EdgeLake website](https://edgelake.github.io/).

The simulation includes the MNIST dataset, where three nodes collaboratively train a global model
with MNIST data local to each node (i.e., there is no data movement.). Since the simulation instructions
are for a single machine, each node will query the same Postgres database but on different tables
so emulate physically distributed data. Nevertheless, each node will utilize its own EdgeLake 
operator node (running in a Docker container) to truly simulate a distributed environment.

In addition, there is another example custom data handle from our Winniio partners. This dataset
is comprised of room temperature data used to predict the temperature of a classroom in two hours.

Before you get started, please follow the configuration steps precisely.

# Configuration
Assumptions:
 - Downloaded / cloned the repository.
 - Have Docker installed.

Install all necessary Python packages. Tested on Python3.12.
```bash
cd Anylog-Edgelake-Federated-Learning-Platform
pip install -r requirements.txt
```

## Deploy Postgres container
Postgres will become available on your inet IP address. You can determine this through the `ifconfig` command. 
```bash
* Start Docker *
cd EdgeLake/postgres
docker compose up -d
```

## Deploy EdgeLake Master node
```bash
cd EdgeLake/
make up EDGELAKE_TYPE=master TAG=1.3.2501 EDGELAKE_SERVER_PORT=32048 EDGELAKE_REST_PORT=32049 NODE_NAME=master
```
Now we need to determine the Master node's Docker IP address. Issue the following command
```bash
cd EdgeLake/
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' master
```

With this IP, we can now deploy our three EdgeLake operator nodes. For example, let's assume it's `192.1.1.1`.

## Deploy EdgeLake Operator node
Update line 61 (LEDGER_CONN) value in the file `EdgeLake/docker_makefile/edgelake_operator1.env`
to be `LEDGER_CONN=192.1.1.1:32048` (note that you do not need to change the port).
In addition, update the `DB_IP` in line 31 with the Docker network IP of the Postgres container. 

Do the same for the following files:
- `EdgeLake/docker_makefile/edgelake_operator2.env`
- `EdgeLake/docker_makefile/edgelake_operator3.env`

Now we can start the operator nodes.
```bash
cd EdgeLake/
make up EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32148 EDGELAKE_REST_PORT=32149 NODE_NAME=operator1
make up EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32248 EDGELAKE_REST_PORT=32249 NODE_NAME=operator2
make up EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32348 EDGELAKE_REST_PORT=32349 NODE_NAME=operator3
```

## Validating your EdgeLake network is properly setup
To  validate your EdgeLake network is properly setup, execute the following commands:
```bash
docker attach master
```
Hit the [enter/return] key on your keyboard. 
You should now see `EL master +>`. 
Now type into the CLI `test network` and press [enter/return]. 
You should see the  following print out:
```bash
EL master +> test network

Test Network
[****************************************************************]

EL master +>
Address          Node Type Node Name Status
----------------|---------|---------|------|
172.19.0.2:32048|master   |master   |  +   |
172.19.0.3:32148|operator |operator1|  +   |
172.19.0.4:32248|operator |operator2|  +   |
172.19.0.5:32348|operator |operator3|  +   |
```
The `+` signifies that the nodes are all members of EdgeLake's p2p network. If you do not see that, then 
please contact the EdgeLake maintainers through [EdgeLake's Slack Channel](https://lfedge.org/projects/edgelake/)
(the join link is at the bottom of the page).

## Setting up training node and aggregator configurations
We now need to update the env files in the `edgefl/env_files/mnist/` directory. To do this, we need to update
the listed variables in the following files `mnist1.env`, `mnist2.env`, `mnist3.env` with the inet IP (e.g., `192.1.1.1`):
- `EXTERNAL_IP`
- `EXTERNAL_TCP_IP_PORT`
- `PSQL_HOST`  

Note that you do not need to change the ports, they're preconfigured to work. 

In addition, update the IP address in for the `EXTERNAL_TCP_IP_PORT` and `EXTERNAL_IP` in the `mnist-agg.env` file.

Now we are ready to start the simulation.

# Running Simulation
The first step is to load data the MNIST data to the Postgres database. 

## Loading Data Instructions
Note that this only needs to be done once. This will create 3 tables `node_node1`, `node_node2`, `node_node3` 
in the `mnist_fl` database. 
```bash
cd edgefl
dotenv -f env_files/mnist/mnist1.env run -- python -m data.mnist.mnist_db_script
```

If you want to train on more (or less) data edit lines `153` and `154` in `edgefl/data/mnist/mnist_db_script.py`.
Moreover, if you'd like to train over more than 10 rounds, edit line `152`. 
Note that training on more data will result in a model with higher accuracy at the model inference step below.

Now that data is loaded into the database continue to the next step.

## Starting aggregator and training nodes
Note to execute the below commands in a new terminal. 
```bash
cd edgefl
dotenv -f env_files/mnist/mnist-agg.env run -- uvicorn platform_components.aggregator.aggregator_server:app --host 0.0.0.0 --port 8080
dotenv -f env_files/mnist/mnist1.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8081
dotenv -f env_files/mnist/mnist2.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8082
dotenv -f env_files/mnist/mnist3.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8083
```

Once all the nodes are running. We can start the training process. Note that you can view the 
predefined training application file here: `edgefl/platform_components/data_handlers/custom_data_handler.py`.

## Initialize model parameters and training application, start training, executing inference
Execute the following `curl` command to initialize training. As a result of this command,
each of the training nodes should be printing out a set of model weights to the screen.
If you do not see this, then your data connector is correctly set up. Please see the resolving
common issues section below.

To initialize training do the following:
```bash
curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081",
    "http://localhost:8082",
    "http://localhost:8083"
  ],
  "index": "test-index"
}'
```
After, start the training process:
```bash
curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 10,
  "minParams": 3
}'
```

`totalRounds` defines how many continuous rounds to train for. `minParams` defines how many parameters
the aggregator should wait for before starting the next round.

At any point during the training process, you can add additional nodes to the process by calling initialization again on the new nodes 
(must use the same `index`) and `minParams` will be dynamically adjusted as necessary.
```bash
curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8084"
  ],
  "index": "test-index"
}'
```

You can also update `minParams` as well during the training process (or anytime after node initialization). The specified `index`
must exist in order to update `minParams`.
```bash
curl -X POST http://localhost:8080/update-minParams \
-H "Content-Type: application/json" \
-d '{
  "updatedMinParams": 3,
  "index": "test-index"
}'
```

Once the training process is complete, you may choose to do additional rounds of training on the same model.
```bash
curl -X POST http://localhost:8080/continue-training \
 -H "Content-Type: application/json" \
 -d '{
   "additionalRounds": 3, 
   "minParams": 4
 }'
 ```

At any point, you can execute edge inference directly on the node.
This can be done on each training node. The output will be the accuracy based on the local test data
held out from training.
```bash
curl -X POST http://localhost:8081/inference
curl -X POST http://localhost:8082/inference
curl -X POST http://localhost:8083/inference
curl -X POST http://localhost:8084/inference
```

An example output looks like this:
```bash
curl -X POST http://localhost:8081/inference ; curl -X POST http://localhost:8082/inference ; curl -X POST http://localhost:8083/inference ; curl -X POST http://localhost:8084/inference
{"message":"Inference completed successfully","model_accuracy":"92.0","status":"success"}
{"message":"Inference completed successfully","model_accuracy":"88.0","status":"success"}
{"message":"Inference completed successfully","model_accuracy":"86.0","status":"success"}
{"message":"Inference completed successfully","model_accuracy":"84.0","status":"success"}
```

## Resolving common issues
After executing the init `curl` request, if your training nodes do not print out model weights,
then they do not have access to the data. 
The first step is to double check that you loaded data into your Postgres instance.
Make sure that you have the following:
1. `mnist_fl` database
2. Three tables: `node_node1`, `node_node2`, `node_node3`
3. Make sure there's actually data in those tables. 

Another step to double check is that the EdgeLake operator nodes are connected to the database.  
To do so you can docker attach to each container and check.
For example, to check `operator1` is connected to the PSQL database, issue the following commands:
```bash
docker attach operator1
```
press [enter/return] so you see `EL master +>`.
Now to validate your PSQL connection, do the following:
```bash
get databases
```
You should see the following:
```bash
EL operator1 +> get databases

Active DBMS Connections
Logical DBMS Database Type Owner  IP:Port            Configuration                       Storage
------------|-------------|------|------------------|-----------------------------------|----------|
almgm       |psql         |system|192.168.1.125:5432|Autocommit On, Fsync on            |Persistent|
mnist_fl    |psql         |user  |192.168.1.125:5432|Autocommit Off, Fsync on           |Persistent|
system_query|psql         |system|192.168.1.125:5432|Autocommit Off, Unflagged, Fsync on|Persistent|
```

If you don't see `mnist_fl`, then execute the following EdgeLake specific command:
```bash
connect dbms mnist_fl where type = psql and user = demo and password = passwd and ip = 192.1.1.1 and port = 5432 and memory = true 
```
where the `192.1.1.1` is your inet ip from above. It should output `database connected`. 
If not, then your IP may be wrong. 

Note, to detach from EdgeLake, press ctrl+p+q simultaneously. 

## Redoing simulation / Clean up
To redo the simulation, you need to delete the `edgefl/file_write` directory.
In addition, you need to kill and restart the EdgeLake operators and master node.
To do so, follow the following instructions:
```bash
cd EdgeLake/
make clean EDGELAKE_TYPE=master TAG=1.3.2501 EDGELAKE_SERVER_PORT=32048 EDGELAKE_REST_PORT=32049 NODE_NAME=master
make clean EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32148 EDGELAKE_REST_PORT=32149 NODE_NAME=operator1
make clean EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32248 EDGELAKE_REST_PORT=32249 NODE_NAME=operator2
make clean EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32348 EDGELAKE_REST_PORT=32349 NODE_NAME=operator3
```
Note that you do not need to restart Postgres.
After this step, if you want to restart the simulation follow the Deploy EdgeLake Operator/Master Node from above.

To stop Postgres:
```bash
cd EdgeLake/postgres
docker compose down
```

# Running Visualization
Change the ips of the prometheus.yml file. You can obtain it by entering ifconfig into terminal. Apply the ip address to all of the nodes and the master node.
```bash
  - job_name: 'master'
    static_configs:
      - targets: ['Your IP:8000']
```
Need to start the docker container for grafana and prometheus 
```bash
cd EdgeLake/docker_makefile/monitoring
docker compose up -d
```
Load up http://localhost:3000/ in your browser and enter username: admin password: admin




# ============ Please Ignore below, README being refactored ============== 

<!-- To Do

- Need to add different commands for Mac & Windows
  -->

## Why EdgeLake:

- **Efficiency:** Reduces data transfer by sharing model parameters instead of sharing entire datasets.

- **Performance:** Our distributed system enables high-computation training to be split across multiple nodes, significantly enhancing speed and scalability compared to single-node processing. .

- **Privacy:** Keeps data on nodes, minimizing exposure risks and enhancing security with privacy-preserving technologies such as blockchain.

# AnyLog-Edgelake Setup Guide

This guide will walk you through setting up and running the AnyLog-Edgelake system.

<!-- ## Prerequisites -->
<!-- we need specify more stuff here -->

## Software Requirements

- Python 3.12
- Git
- Ability to run shell scripts
- cURL (for API requests)
- EdgeLake (to run the aggregator and nodes)
- _Optional_: PyCharm \[Professional Edition\]

## Installation Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/royshadmon/Anylog-Edgelake-CSE115D.git
   ```

2. Configure Environment Variables:

    Note that there are currently two datasets in `edgefl/data`: _mnist_ and _winniio_.
    For this setup, we will use the winniio dataset and configure for it.

    - Navigate to `Anylog-Edgelake-CSE115D/edgefl/env_files`

   ```bash
   cd Anylog-Edgelake-CSE115D/edgefl/env_files
   ```

    - Locate `winniio.env` in the directory
    - Modify these variables in the file:

        - `EXTERNAL_IP`: Replace the IP portion with your machine's IP address.
                You can fetch them in the terminal using the command `ifconfig` on
                Mac/Linux, found under `inet`/`en0`(`ipconfig` on Windows under `IPv4`).
        - `EXTERNAL_TCP_IP_PORT`: Do the same process done for `EXTERNAL_IP`.
        - `PSQL_DB_USER`: Set this to the user for the database that will be used.
        - `PSQL_DB_PASSWORD`: If you have a password for the user, set this to it.
        - `FILE_WRITE_DESTINATION`: Set this path to `[/path/to]/Anylog-Edgelake-CSE115D/edgegl/file_write`

    - Notes:
    
        - If your database will not be locally hosted, set `PSQL_DB_HOST` accordingly.
        - If you have specified the port of your database, set `PSQL_DB_PORT` accordingly.

3. Install pip:

    - Navigate back to `Anylog-Edgelake-CSE115D/` and run the following:

   ```
   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
   python3.12 get-pip.py
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Set up and start a Postgres instance

    - [Postgres Mac instructions](https://www.sqlshack.com/setting-up-a-postgresql-database-on-mac/)

6. Set up and load data into Postgres

    - In `Anylog-Edgelake-CSE115D/`, navigate to `edgefl/data/winniio-rooms/linode-setup/`
    - Locate `winniio_db_script.py` and ensure that it is configured to get ENV variables from
        `winniio.env`.
        - On PyCharm, you can edit the configuration of the script and specify the
            .env file in _Path(s) to ".env" files_
    - Run the script to load the winniio dataset:
      ```bash
      ./winniio_db_script
      ```

8. Start the Servers:

    - The following script has not yet been updated (eventually):

   ```bash
   ./start_servers.sh
   ```
   
    - Instead, start each node server and the one aggregator server manually.
    
        - The aggregator server file and node server file are located in
            `edgefl/platform_components/aggregator/` and
            `edgefl/platform_components/node/`, respectively.
        - Run `/aggregator/aggregator_server.py` to start the aggregator server.
        - Run `/aggregator/node_server.py` to start a node server.

    - **Notes**:

        - For each server file ran, ensure that you've load the ENV variables
            from the env files.
        - For each node server, make sure you've specified their ports (8081,
            8082, etc.).
            - If you're using PyCharm, you can edit the configuration
                of `node_server.py` and add this to _script parameters_:
                `--p [next available port]`. You can also create a new
                configuration for each node server you want to start for convenience.

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


## Parameters Explained

### Initialization Parameters
- `nodeUrls`: Array of URLs for the participating nodes

### Training Parameters
- `totalRounds`: Number of training rounds to perform
- `minParams`: Minimum number of parameters required (default: 1)

## Troubleshooting

If you encounter any issues:
1. Ensure all servers are running properly
2. Check that the `.env` file is configured correctly
3. Verify all ports (8080, 8081, 8082) are available
4. Make sure all the software requirements are properly installed \
~~5. If servers aren't responding, try killing them with `./kill_servers.sh` and restart~~

## MongoDB (for file handling) [Mongo is currently deprecated, we will need to re-add this feature]

### Install / setup (Mac)

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

### Install / setup (for Ubuntu machines)

```bash
wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | sudo apt-key add -  
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/5.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-5.0.list
sudo apt-get update
sudo apt-get install -y mongodb-mongosh
mongosh --version
```

[Mongo Ubuntu Setup](https://www.slingacademy.com/article/how-to-install-mongodb-shell-mongosh-on-windows-mac-and-ubuntu/)

### Start MongoDB Mac
```bash
brew services start mongodb-community
mongod --dbpath /usr/local/bin/mongodb/var/mongodb --logpath /usr/local/bin/mongodb/log/mongodb/mongo.log
```
