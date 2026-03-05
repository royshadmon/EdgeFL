# EdgeFL

## Overview

EdgeFL simulates a continuous Federated Learning (FL) lifecycle with three training nodes and one aggregator node. Each node connects to either an **AnyLog** or **EdgeLake** backend (choose one). You'll deploy four backend nodes: three operators and one master. The master emulates blockchain-like shared metadata functionality.

EdgeFL supports three demos where each operator locally trains a model using its own data. EdgeFL dynamically facilitates model sharing and aggregation via the aggregator—**no data movement required**. 

Since these instructions target a single machine (adaptable to multiple), we deploy multiple Postgres databases (one per operator) to emulate distributed data. Each node runs in a Docker container to simulate a true distributed environment.

**Supported backends:**
- **AnyLog** (primary): Requires license key and Docker image. See [AnyLog Setup Guide](Demo-READMEs/AnyLog-Setup.md) for detailed steps.
- **EdgeLake** (alternative, open-source): See [EdgeLake Setup Guide](Demo-READMEs/EdgeLake-Setup.md) for detailed steps.

For more about EdgeLake, visit the [EdgeLake website](https://edgelake.github.io/).

Before you get started, please follow the configuration steps precisely.

# Configuration

## Prerequisites
- Docker Desktop installed and running
- Git with repository cloned
- **AnyLog users only:** AnyLog license key and Docker image loaded (see [AnyLog Setup Guide](Demo-READMEs/AnyLog-Setup.md) sections 2-4)

## Python Environment Setup
```bash
cd EdgeFL
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
pip3 install torch torchvision requests tensorflow scikit-learn dotenv "python-dotenv[cli]" uvicorn fastapi docker requests_toolbelt
```

## Deploy Postgres Databases
You need three Postgres containers (one per operator). Postgres will be available on your inet IP (check with `ifconfig`).

**EdgeLake users:**
```bash
cd EdgeLake/postgres
make up NAME=postgres1 HOST_PORT=5432 VOLUME=pgdata1
make up NAME=postgres2 HOST_PORT=5433 VOLUME=pgdata2
make up NAME=postgres3 HOST_PORT=5434 VOLUME=pgdata3
```

**AnyLog users:**
```bash
cd docker-compose/support-tools/postgres
make up NAME=postgres1 HOST_PORT=5432 VOLUME=pgdata1
make up NAME=postgres2 HOST_PORT=5433 VOLUME=pgdata2
make up NAME=postgres3 HOST_PORT=5434 VOLUME=pgdata3
```

You can customize `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` in the Makefile or as arguments.

To stop:
```bash
make clean NAME=postgres1 VOLUME=pgdata1
make clean NAME=postgres2 VOLUME=pgdata2
make clean NAME=postgres3 VOLUME=pgdata3
```

## Deploy Backend Nodes (AnyLog or EdgeLake)

### Deploy Master Node

**EdgeLake:**
```bash
cd EdgeLake/
make up EDGELAKE_TYPE=master TAG=1.3.2501 EDGELAKE_SERVER_PORT=32048 EDGELAKE_REST_PORT=32049 NODE_NAME=master
```

**AnyLog:**
```bash
# Export license first
export ANYLOG_LICENSE="<your-license-key>"

cd docker-compose/
make up ANYLOG_TYPE=master
```

Get the master node's Docker IP:
```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' master
```
Save this IP (e.g., `192.1.1.1`) for operator configuration.

### Deploy Operator Nodes

**Configure operator env files** with the master IP and Postgres IPs:

**EdgeLake:** Update `LEDGER_CONN` and `DB_IP` in:
- `EdgeLake/docker_makefile/edgelake_operator1.env`
- `EdgeLake/docker_makefile/edgelake_operator2.env`
- `EdgeLake/docker_makefile/edgelake_operator3.env`

**AnyLog:** Update similar fields in:
- `docker-compose/docker_makefile/anylog_operator1.env`
- `docker-compose/docker_makefile/anylog_operator2.env`
- `docker-compose/docker_makefile/anylog_operator3.env`

**Start operators:**

**EdgeLake:**
```bash
cd EdgeLake/
make up EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32148 EDGELAKE_REST_PORT=32149 NODE_NAME=operator1
make up EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32248 EDGELAKE_REST_PORT=32249 NODE_NAME=operator2
make up EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32348 EDGELAKE_REST_PORT=32349 NODE_NAME=operator3
```

**AnyLog:**
```bash
cd docker-compose/
make up ANYLOG_TYPE=operator1
make up ANYLOG_TYPE=operator2
make up ANYLOG_TYPE=operator3
```

## Validate Backend Network

Attach to the master node and test network connectivity:
```bash
docker attach master
```
Press [enter/return]. You should see `EL master +>` (EdgeLake) or `AL master +>` (AnyLog).

Test network:
```bash
test network
```

Expected output (all nodes show `+` status):
```
Test Network
[****************************************************************]

Address          Node Type Node Name Status
----------------|---------|---------|------|
172.19.0.2:32048|master   |master   |  +   |
172.19.0.3:32148|operator |operator1|  +   |
172.19.0.4:32248|operator |operator2|  +   |
172.19.0.5:32348|operator |operator3|  +   |
```

If nodes don't show `+`, check your `LEDGER_CONN` configuration in operator env files. For EdgeLake support, see [EdgeLake Slack](https://lfedge.org/projects/edgelake/).

### Verify Database Connections

Attach to an operator and check databases:
```bash
docker attach operator1
```
Press [enter/return] to see the prompt.

Check database connections:
```bash
get databases
```

Expected output:
```
Active DBMS Connections
Logical DBMS Database Type Owner  IP:Port            Configuration                       Storage
------------|-------------|------|------------------|-----------------------------------|----------|
almgm       |psql         |system|192.168.1.125:5432|Autocommit On, Fsync on            |Persistent|
mnist_fl    |psql         |user  |192.168.1.125:5432|Autocommit Off, Fsync on           |Persistent|
system_query|psql         |system|192.168.1.125:5432|Autocommit Off, Unflagged, Fsync on|Persistent|
```

If `mnist_fl` is missing, connect it:
```bash
connect dbms mnist_fl where type = psql and user = demo and password = passwd and ip = [postgres-ip] and port = 5432 and memory = true
```

### Verify Tables and Data

View all tables in the `mnist_fl` database:
```bash
get tables where dbms = mnist_fl
```

Expected output:
```
Database Table name                                           Local DBMS Blockchain
--------|----------------------------------------------------|----------|----------|
mnist_fl|mnist_test                                          | V        | V        |
        |mnist_train                                         | V        | V        |
        |par_mnist_train_2025_07_01_d14_insert_timestamp     | V        | -        |
```

View tables hosted by each operator:
```bash
get data nodes
```

Expected output:
```
Company     DBMS     Table            Cluster ID                       Cluster Status Node Name Member ID External IP/Port    Local IP/Port    Main Node Status
-----------|--------|----------------|--------------------------------|--------------|---------|---------|-------------------|----------------|----|-----------|
New Company|mnist_fl|mnist_train     |1a4a2c6f59161cf5f7b242abcacf6ba2|active        |operator1|       79|104.60.100.77:32148|172.17.0.3:32148| +  |active     |
           |        |                |                                |active        |operator2|      208|104.60.100.77:32248|172.17.0.4:32248| +  |active     |
           |        |                |                                |active        |operator3|       65|104.60.100.77:32348|172.17.0.5:32348| +  |active     |
New Company|mnist_fl|mnist_test      |1a4a2c6f59161cf5f7b242abcacf6ba2|active        |operator1|       79|104.60.100.77:32148|172.17.0.3:32148| +  |active     |
           |        |                |                                |active        |operator2|      208|104.60.100.77:32248|172.17.0.4:32248| +  |active     |
           |        |                |                                |active        |operator3|       65|104.60.100.77:32348|172.17.0.5:32348| +  |active     |
```

View row count by operator:
```bash
get rows count where dbms=mnist_fl
```

Expected output:
```
DBMS Name Table Name                                           Rows Count
---------|----------------------------------------------------|----------|
mnist_fl |mnist_test                                          |         0|
         |mnist_train                                         |         0|
         |par_mnist_train_2025_07_01_d14_insert_timestamp     |        50|
```

Query data directly:
```bash
run client (192.168.1.125:32148) sql mnist_fl select count(*) from mnist_train
```

Expected output:
```
{"Query":[{"count(*)":50}],
"Statistics":[{"Count": 1,
                "Time":"00:00:00",
                "Nodes": 1}]}
```

**To detach from a container:** Press `Ctrl+P` then `Ctrl+Q` (do NOT use `Ctrl+C` or `exit`).

# Running EdgeFL Demos

EdgeFL supports three demos. The following shows the unified setup for MNIST (the most common demo). For other demos and platform-specific details, see the guides below.

**Detailed setup guides:**
- [AnyLog Setup Guide (Apple Silicon)](Demo-READMEs/AnyLog-Setup.md) — Primary method with license
- [EdgeLake Setup Guide (Apple Silicon)](Demo-READMEs/EdgeLake-Setup.md) — Open-source alternative
- [MNIST demo details](Demo-READMEs/MNIST.md)
- [Winniio temperature prediction](Demo-READMEs/WINNIIO.md)
- [Chest X-ray bounding box](Demo-READMEs/Chest-Xray-BoundingBox.md)

## MNIST Demo Setup

### Configure EdgeFL Environment Files

Edit files in `edgefl/env_files/mnist/` and set:
- `GITHUB_DIR` to your EdgeFL repo path (e.g., `/Users/yourname/Desktop/Code/EdgeFL`)
- `EXTERNAL_IP` and `EXTERNAL_TCP_IP_PORT` to localhost ports (recommended when using port forwarding):

| File           | EXTERNAL_IP (REST) | EXTERNAL_TCP_IP_PORT (TCP) |
|----------------|-------------------|---------------------------|
| mnist-agg.env  | 127.0.0.1:32049   | 127.0.0.1:32048          |
| mnist1.env     | 127.0.0.1:32149   | 127.0.0.1:32148          |
| mnist2.env     | 127.0.0.1:32249   | 127.0.0.1:32248          |
| mnist3.env     | 127.0.0.1:32349   | 127.0.0.1:32348          |

> **Note:** If you get SQL connection errors, try `EXTERNAL_TCP_IP_PORT="network"` instead.

### Insert MNIST Data

```bash
cd edgefl/data/mnist
python3 store_data.py 127.0.0.1:32149 --db-name mnist_fl
python3 store_data.py 127.0.0.1:32249 --db-name mnist_fl
python3 store_data.py 127.0.0.1:32349 --db-name mnist_fl
```

### Start EdgeFL Servers

Open 4 terminals and run the following (from `EdgeFL/edgefl`):

**Terminal 1 — Aggregator:**
```bash
cd edgefl
source ../.venv/bin/activate
python3 -m dotenv -f env_files/mnist/mnist-agg.env run -- \
  python3 -m uvicorn platform_components.aggregator.aggregator_server:app --host 0.0.0.0 --port 8080
```

**Terminal 2 — Node 1:**
```bash
cd edgefl
source ../.venv/bin/activate
dotenv -f env_files/mnist/mnist1.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8081
```

**Terminal 3 — Node 2:**
```bash
cd edgefl
source ../.venv/bin/activate
dotenv -f env_files/mnist/mnist2.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8082
```

**Terminal 4 — Node 3:**
```bash
cd edgefl
source ../.venv/bin/activate
dotenv -f env_files/mnist/mnist3.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8083
```

All should show `Uvicorn running on http://0.0.0.0:80XX` with no errors.

### Train and Infer

Initialize nodes:
```bash
curl -X POST http://localhost:8080/init \
  -H "Content-Type: application/json" \
  -d '{"nodeUrls":["http://localhost:8081","http://localhost:8082","http://localhost:8083"],"index":"test-index"}'
```

Start training:
```bash
curl -X POST http://localhost:8080/start-training \
  -H "Content-Type: application/json" \
  -d '{"totalRounds":10,"minParams":3,"index":"test-index"}'
```

Run inference (against a **node**, not the aggregator):
```bash
curl -X POST http://localhost:8081/inference/test-index
```

### Web GUI (Optional but Recommended)

From `EdgeFL/`:
```bash
cd gui/edgefl-gui
npm install
npm start
```

In the GUI:
1. Enter test index name and node URLs (`http://localhost:8081`, etc.)
2. Click **Init** — all nodes should succeed
3. Click **Next**, configure training, click **Start Training**
4. After training, click **Inference**
5. Update top-right URL to a **node** (e.g., `http://localhost:8081`), NOT the aggregator
6. Test inference (drawing recommended)


## Cleanup

To stop and clean up:

**Stop EdgeFL servers:** Press `Ctrl+C` in each terminal.

**Stop backend nodes:**

**EdgeLake:**
```bash
cd EdgeLake/
make clean EDGELAKE_TYPE=master TAG=1.3.2501 EDGELAKE_SERVER_PORT=32048 EDGELAKE_REST_PORT=32049 NODE_NAME=master
make clean EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32148 EDGELAKE_REST_PORT=32149 NODE_NAME=operator1
make clean EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32248 EDGELAKE_REST_PORT=32249 NODE_NAME=operator2
make clean EDGELAKE_TYPE=operator TAG=1.3.2501 EDGELAKE_SERVER_PORT=32348 EDGELAKE_REST_PORT=32349 NODE_NAME=operator3
```

**AnyLog:**
```bash
cd docker-compose/
make clean ANYLOG_TYPE=master
make clean ANYLOG_TYPE=operator1
make clean ANYLOG_TYPE=operator2
make clean ANYLOG_TYPE=operator3
```

**Stop Postgres:**
```bash
# EdgeLake users: cd EdgeLake/postgres
# AnyLog users: cd docker-compose/support-tools/postgres
make clean NAME=postgres1 VOLUME=pgdata1
make clean NAME=postgres2 VOLUME=pgdata2
make clean NAME=postgres3 VOLUME=pgdata3
```

**Clean EdgeFL artifacts:**
```bash
rm -rf edgefl/file_write/*
rm -rf edgefl/tmp_dir/*
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Training nodes don't print model weights | Check data was inserted to Postgres (`mnist_fl` database with `mnist_train`/`mnist_test` tables). Verify operator database connections with `get databases` (see [Validate Backend Network](#validate-backend-network)). |
| `curl` to node returns connection error | Enable **host networking** in Docker Desktop settings and restart Docker. |
| Nodes don't show `+` in `test network` | Check `LEDGER_CONN` in operator env files points to correct master IP. |
| `mnist_fl` database not connected | Attach to operator, run `connect dbms mnist_fl where type = psql and user = demo and password = passwd and ip = [postgres-ip] and port = 5432 and memory = true` |
| SQL query connection errors | Try setting `EXTERNAL_TCP_IP_PORT="network"` in env files instead of IP:port. | 

---

## Docker Containerization of APIs

The APIs are containerized using Docker. Before starting the APIs, ensure that 
```bash
edgefl/env_files/mnist-docker/mnist1.env
edgefl/env_files/mnist-docker/mnist2.env
edgefl/env_files/mnist-docker/mnist3.env
```
are configured like this:
```bash
GITHUB_DIR=/app/edgefl

TRAINING_APPLICATION_DIR=platform_components/data_handlers
MODULE_NAME=MnistDataHandler

PORT=<operator port num> #(aggregator port num + operator num = operator port num)
SERVER_TYPE=node
TMP_DIR=tmp_dir/node<operator number>/
# External IP Address for CURL commands to Edgelake
EXTERNAL_IP="<EdgeLake ip:port>"
EXTERNAL_TCP_IP_PORT="<EdgeLake ip:port>"

# node that system_query resides on
QUERY_NODE_URL="<EdgeLake ip:port>"
# Edge Node containing data
EDGE_NODE_URL="<EdgeLake ip:port>"
# Logical database name
LOGICAL_DATABASE=mnist_fl
# Table containing trained data
TRAIN_TABLE=room_12055_train
# Table containing test data
TEST_TABLE=room_12055_test

FILE_WRITE_DESTINATION="file_write"

EDGELAKE_DOCKER_RUNNING="True"
EDGELAKE_DOCKER_CONTAINER_NAME="operator<operator number>"
DOCKER_FILE_WRITE_DESTINATION="/app/file_write"
```
The aggregator env file,
```bash
edgefl/env_files/mnist-docker/mnist-agg.env
```

Should be configured like this:
```bash
GITHUB_DIR=/app/edgefl/

TRAINING_APPLICATION_DIR=platform_components/data_handlers
MODULE_NAME=MnistDataHandler

PORT=8080
SERVER_TYPE=aggregator

TMP_DIR=tmp_dir/agg/
# External IP Address for CURL commands to Edgelake
EXTERNAL_IP="<host ip>:32049"
EXTERNAL_TCP_IP_PORT="<host ip>:32048"

# LOCAL PSQL DB NAME
PSQL_DB_NAME="mnist_fl"
PSQL_DB_USER="demo"
PSQL_DB_PASSWORD="passwd"
PSQL_HOST=<host ip>
PSQL_PORT="5432"

FILE_WRITE_DESTINATION="file_write"
AGG_NAME=agg

EDGELAKE_DOCKER_RUNNING="True"
EDGELAKE_DOCKER_CONTAINER_NAME=master
DOCKER_FILE_WRITE_DESTINATION="/app/file_write"
```
To build the image, run the following command from the root directory of the project:

```bash
docker build -t edgefl:latest -f api-containers/Dockerfile .
```

You can run any of the APIs using Docker Compose. The `docker-compose.yml` file in the `api-containers` directory defines the services for the aggregator and nodes.

To run all of the APIs:
```bash
cd api-containers
docker compose up -d
```

The run only specific API services in the `docker-compose.yml` file, you can add the `--no-deps` flag to avoid starting dependent services. This is useful for testing or development purposes. 
The template for running a set of services is as follows:
```bash
cd api-containers
docker compose up -d --no-deps <service1> <service2> ...
```
Where `<service1>`, `<service2>`, etc. are the names of services defined in the `docker-compose.yml` file.


Example A: to run only the Aggregator
```bash
cd api-containers
docker compose up --no-deps -d aggregator
```
Example B: to run the aggregator and two nodes
```bash
cd api-containers
docker compose up --no-deps -d aggregator node1 node2
```
You can then add a node by running the following command:
```bash
docker compose up --no-deps -d node3
```

To see the endpoints and interact with the APIs, you can use the following URLs:
```bash
127.0.0.1:8080/docs # aggregator

127.0.0.1:8081/docs # nodes
127.0.0.1:8082/docs
127.0.0.1:8083/docs
```

To take down the containers, simply run:
```bash
docker compose down
```














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
