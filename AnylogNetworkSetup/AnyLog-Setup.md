# AnyLog Setup Guide (Apple Silicon)

This is the **primary method** for running EdgeFL with AnyLog on Apple Silicon Macs. For the EdgeLake alternative, see [EdgeLake-Setup.md](./EdgeLake-Setup.md).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Docker Image Setup](#2-docker-image-setup)
3. [Docker-Compose Repository](#3-docker-compose-repository)
4. [License Key & Credentials](#4-license-key--credentials)
5. [AnyLog Configuration](#5-anylog-configuration)
6. [PostgreSQL Setup](#6-postgresql-setup)
7. [Start AnyLog Nodes](#7-start-anylog-nodes)
8. [EdgeFL Environment Setup](#8-edgefl-environment-setup)
9. [Insert MNIST Data](#9-insert-mnist-data)
10. [Run Training](#10-run-training)
11. [Inference](#11-inference)
12. [Web GUI (Optional)](#12-web-gui-optional)
13. [Quick Start (Returning Users)](#13-quick-start-returning-users)
14. [Cleanup](#14-cleanup)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Prerequisites

- **Docker Desktop** — installed and running
- **AnyLog Docker image** — Currently not publicly available. For those interested in trying AnyLog, fill out the form at https://www.anylog.network/download to receive a license key and email roy[at]anylog[dot]co for more information.
- **docker-compose (latest)** — install via Homebrew (`brew install docker-compose`); older versions may cause issues
- **Python 3.10+** with `venv` support

---

## 2. Docker Image Setup

Load the AnyLog Docker image (ARM or AMD) and verify it:

```bash
docker load < /path/to/AnyLog-[ARCHITECTURE].tar

docker image ls | grep anylog
# Expected: anylogco/anylog-network   [TAG]   <image-id>   ~789MB
```

Note the image tag from the output — you'll need it in the configuration step.

---

## 3. Docker-Compose Repository

> **Note:** These setup instructions are for **local environment only**. For instructions on deploying AnyLog globally, reach out to the AnyLog team.

Clone and check out the correct branch:

```bash
git clone https://github.com/AnyLog-co/docker-compose.git
cd docker-compose
git checkout roy-local
git pull origin roy-local
```

---

## 4. License Key & Credentials

### Create the credentials file

Export your AnyLog license key to a file in a directory of your choice. For example:

```bash
mkdir -p [YOUR_CREDENTIALS_DIRECTORY]
```

Create `[YOUR_CREDENTIALS_DIRECTORY]/.anylog_key.env` with your license key:

```
ANYLOG_LICENSE="56b3d57....269ff{'company':'Guest','expiration':'somedate','type':'beta'}"
```

### Source the key

Add the following to your shell profile (e.g. `~/.zshrc`) so it loads automatically:

```bash
source [YOUR_CREDENTIALS_DIRECTORY]/.anylog_key.env
export ANYLOG_LICENSE
```

Otherwise, source it manually in each terminal session. Verify with:

```bash
echo $ANYLOG_LICENSE
```

---

## 5. AnyLog Configuration

All commands below assume you are in the `docker-compose` repository root.

### 5a. Set the Docker image tag

In the repo's `Makefile`, change line 7 to match your AnyLog image tag:

```makefile
export TAG ?= [YOUR_IMAGE_TAG]
```

To find your image tag, run `docker image ls | grep anylog` and use the tag from the output.

### 5b. Set the license key in the master config

In `docker-makefiles/master-configs/base_configs.env`, change:

```
LICENSE_KEY=""
```

to:

```
LICENSE_KEY=$ANYLOG_LICENSE
```

### 5c. Set required base config settings

In every base config file (master and operators: `docker-makefiles/master-configs/base_configs.env`, `docker-makefiles/operator1-configs/base_configs.env`, etc.), ensure the following are set:

```env
TCP_BIND=true
REST_BIND=true
BROKER_BIND=false
```
Otherwise, you might experience issues with network connectivity with multiple IP addresses per node.

### 5d. Disable NoSQL/Blobs in each operator config

In every operator base config file (e.g. `docker-makefiles/operator1-configs/base_configs.env`, etc.), set:

```env
ENABLE_NOSQL=false
BLOBS_DBMS=false
BLOBS_STORAGE=false
```

---

## 6. PostgreSQL Setup

From the `docker-compose` repo, start three PostgreSQL containers (one per operator):

```bash
cd support-tools/postgres

make up NAME=postgres1 HOST_PORT=5432 VOLUME=pgdata1
make up NAME=postgres2 HOST_PORT=5433 VOLUME=pgdata2
make up NAME=postgres3 HOST_PORT=5434 VOLUME=pgdata3
```

---

## 7. Start AnyLog Nodes

Return to the `docker-compose` repo root. Make sure the license is exported:

```bash
export ANYLOG_LICENSE
```

### 7a. Start the master node

```bash
make up ANYLOG_TYPE=master
```

**Validate:**

```bash
docker attach master
# Press Enter a few times, then type:
test network
```

Expected output:

```
Address         Node Type Node Name Status
---------------|---------|---------|------|
127.0.0.1:32048|master   |master   |  +   |
```

Detach with `Ctrl+P`, `Ctrl+Q`.

### 7b. Start the operator nodes

```bash
make up ANYLOG_TYPE=operator1
make up ANYLOG_TYPE=operator2
make up ANYLOG_TYPE=operator3
```

**Validate** (attach to any operator):

```bash
docker attach operator1
# wait a few seconds, then press Enter a few times, then type:
test network
```

Expected output — all four nodes with `+` status:

```
Address         Node Type Node Name Status
---------------|---------|---------|------|
127.0.0.1:32048|master   |master   |  +   |
127.0.0.1:32148|operator |operator1|  +   |
127.0.0.1:32248|operator |operator2|  +   |
127.0.0.1:32348|operator |operator3|  +   |
```

### 7c. Verify databases

While attached to an operator:

```
get databases
```

You should see `almgm` and `system_query`, and either `customers` or `mnist_fl`:

```
Active DBMS Connections
Logical DBMS Database Type Owner  IP:Port        Configuration                                     Storage    
------------|-------------|------|--------------|-------------------------------------------------|----------|
almgm       |psql         |system|127.0.0.1:5432|Autocommit On, Fsync on                          |Persistent|
mnist_fl    |psql         |user  |127.0.0.1:5432|Autocommit On, Fsync on                          |Persistent|
system_query|sqlite       |system|Local         |Autocommit On, RAM, Fsync full (after each write)|MEMORY    |
```

### 7d. Verify external access

From the host machine in a separate terminal:

```bash
curl --location --request GET http://127.0.0.1:32149 \
  --header "User-Agent: AnyLog/1.23" \
  --header "command: get status"
```

Expected output for example operator1:

```
operator1@127.0.0.1:32148 running
```

> **If this fails:** In Docker Desktop → Settings → Resources → Network, enable **host networking**. Restart Docker.

---

## 8. EdgeFL Environment Setup

### 8a. Python environment

```bash
cd /path/to/EdgeFL
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
pip3 install torch torchvision requests tensorflow scikit-learn dotenv "python-dotenv[cli]" uvicorn fastapi docker requests_toolbelt
```

### 8b. Configure env files

Edit the files in `edgefl/env_files/mnist/`. Each file needs:

- **`GITHUB_DIR`** — absolute path to the EdgeFL repo on your local machine

The port mappings are:

| File           | `EXTERNAL_IP` (REST)  | `EXTERNAL_TCP_IP_PORT` (TCP) |
|----------------|----------------------|------------------------------|
| `mnist-agg.env`| `127.0.0.1:32049`    | `127.0.0.1:32048`            |
| `mnist1.env`   | `127.0.0.1:32149`    | `127.0.0.1:32148`            |
| `mnist2.env`   | `127.0.0.1:32249`    | `127.0.0.1:32248`            |
| `mnist3.env`   | `127.0.0.1:32349`    | `127.00.0.1:32348`            |

> **Note:** If you get SQL query connection errors, try setting `EXTERNAL_TCP_IP_PORT="network"` instead of the IP:port combo.

Make sure all env files use the same data handler (`MODULE_NAME=MnistDataHandler`, `MODULE_FILE=custom_data_handler.py` or `MODULE_NAME=MnistDataHandler`, `MODULE_FILE=mnist_data_handler.py`)

---

## 9. Insert MNIST Data

### 9a. Fix `store_data.py` (if needed)

In `edgefl/data/mnist/store_data.py`, change the two instances of:

```python
"image": img.numpy().flatten().tolist(),
```

to:

```python
"image": json.dumps(img.numpy().flatten().tolist()),
```

### 9b. Insert data into each operator

Insert data into each operator using the logical database name (in this case, `mnist_fl`):

```bash
cd edgefl/data/mnist

python3 store_data.py 127.0.0.1:32149 --db-name mnist_fl
python3 store_data.py 127.0.0.1:32249 --db-name mnist_fl
python3 store_data.py 127.0.0.1:32349 --db-name mnist_fl
```

### 9c. Validate

Attach to any operator and run:

```
blockchain get table
```

You should see two tables: `mnist_train` and `mnist_test`.

Further verification:

```
get tables where dbms = mnist_fl
get data nodes
get streaming
```
should all output non-empty results

---

## 10. Run Training

You need **4 terminal windows**, all with the venv activated. Run each command in a separate terminal from `edgefl/`:

**Terminal 1 — Aggregator:**

```bash
python3 -m dotenv -f env_files/mnist/mnist-agg.env run -- \
  python3 -m uvicorn platform_components.aggregator.aggregator_server:app --host 0.0.0.0 --port 8080
```

**Terminal 2 — Node 1:**

```bash
dotenv -f env_files/mnist/mnist1.env run -- \
  uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8081
```

**Terminal 3 — Node 2:**

```bash
dotenv -f env_files/mnist/mnist2.env run -- \
  uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8082
```

**Terminal 4 — Node 3:**

```bash
dotenv -f env_files/mnist/mnist3.env run -- \
  uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8083
```

All should show `Uvicorn running on http://0.0.0.0:80XX` with no errors.

### 10a. Initialize 

These steps can also be done through the GUI (see [Section 12](#12-web-gui-optional-but-recommended)).

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

Each node terminal should print:

```
[INFO] nodeX successfully initialized for (test-index)
[INFO] [test-index][Round 1] Listening for start round 1
```

### 10b. Start training

```bash
curl -X POST http://localhost:8080/start-training \
  -H "Content-Type: application/json" \
  -d '{
    "totalRounds": 10,
    "minParams": 3,
    "index": "test-index"
  }'
```

- **`totalRounds`** — number of federated rounds
- **`minParams`** — how many node weights the aggregator waits for before aggregating

---

## 11. Inference

After training completes, test each node:

```bash
curl -X POST http://localhost:8081/inference/test-index
curl -X POST http://localhost:8082/inference/test-index
curl -X POST http://localhost:8083/inference/test-index
```

Example response:

```json
{"index":"test-index","status":"success","message":"Inference completed successfully","model_accuracy":"92.0"}
```

---

## 12. Web GUI (Optional but Recommended)

Instead of using `curl`, you can use the built-in GUI.

From `EdgeFL/`:
```bash
cd gui/edgefl-gui
npm install
npm start
```

In the GUI:
1. Enter a test index name and the node URLs (`http://localhost:8081`, etc.)
2. Click **Init** — all nodes should succeed
3. Click **Next**, configure training parameters, and click **Start Training**
4. Once training is complete, click **Inference**. 
5. Update the top right corner to the node URL/Port you used for an operator, NOT the aggregator.
6. Test any of the inference options provided (drawing recommended).

---

## 13. Quick Start (Returning Users)

> This assumes all configuration and first-time setup is already done.

### Start infrastructure

```bash
# Export license
export ANYLOG_LICENSE

# PostgreSQL (from docker-compose/support-tools/postgres/)
cd docker-compose/support-tools/postgres/
make up NAME=postgres1 HOST_PORT=5432 VOLUME=pgdata1
make up NAME=postgres2 HOST_PORT=5433 VOLUME=pgdata2
make up NAME=postgres3 HOST_PORT=5434 VOLUME=pgdata3

# AnyLog nodes (from docker-compose/)
cd ../
make up ANYLOG_TYPE=master
make up ANYLOG_TYPE=operator1
make up ANYLOG_TYPE=operator2
make up ANYLOG_TYPE=operator3
```

### Insert data

```bash
cd EdgeFL
source .venv/bin/activate
cd edgefl/data/mnist

python3 store_data.py 127.0.0.1:32149 --db-name mnist_fl
python3 store_data.py 127.0.0.1:32249 --db-name mnist_fl
python3 store_data.py 127.0.0.1:32349 --db-name mnist_fl
```

### Start servers (4 terminals, each with venv activated, from `edgefl/`)

```bash
# Terminal 1: Aggregator
cd edgefl
python3 -m dotenv -f env_files/mnist/mnist-agg.env run -- \
  python3 -m uvicorn platform_components.aggregator.aggregator_server:app --host 0.0.0.0 --port 8080

# Terminal 2: Node 1
cd edgefl
source ../.venv/bin/activate
dotenv -f env_files/mnist/mnist1.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8081

# Terminal 3: Node 2
cd edgefl
source ../.venv/bin/activate
dotenv -f env_files/mnist/mnist2.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8082

# Terminal 4: Node 3
cd edgefl
source ../.venv/bin/activate
dotenv -f env_files/mnist/mnist3.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8083
```

### Train & infer

```bash
# Init
curl -X POST http://localhost:8080/init \
  -H "Content-Type: application/json" \
  -d '{"nodeUrls":["http://localhost:8081","http://localhost:8082","http://localhost:8083"],"index":"test-index"}'

# Train
curl -X POST http://localhost:8080/start-training \
  -H "Content-Type: application/json" \
  -d '{"totalRounds":10,"minParams":3,"index":"test-index"}'

# Inference (after training completes)
curl -X POST http://localhost:8081/inference/test-index
```




---

## 14. Cleanup

### Stop AnyLog nodes (from `docker-compose/`)

```bash
make clean ANYLOG_TYPE=master
make clean ANYLOG_TYPE=operator1
make clean ANYLOG_TYPE=operator2
make clean ANYLOG_TYPE=operator3
```

### Stop PostgreSQL (from `docker-compose/support-tools/postgres/`)

```
cd support-tools/postgres/
```

Without deleting data:

```bash
make down NAME=postgres1
make down NAME=postgres2
make down NAME=postgres3
```

With deleting data:

```bash
make clean NAME=postgres1 VOLUME=pgdata1
make clean NAME=postgres2 VOLUME=pgdata2
make clean NAME=postgres3 VOLUME=pgdata3
```

### Remove leftover Docker volumes (shouldn't be necessary with make clean)

```bash
docker volume ls
docker volume rm $(docker volume ls -q | grep '^docker-compose-files_')
```

---

## 15. Troubleshooting

| Problem | Solution |
|---------|----------|
| `curl` to node returns connection error | Enable **host networking** in Docker Desktop settings and restart Docker |
| `TypeError: expected string or bytes-like object, got 'list'` in `store_data.py` | Wrap the image list with `json.dumps()` (see [Section 9a](#9a-fix-store_datapyif-needed)) |
| SQL query connection error from nodes | Set `EXTERNAL_TCP_IP_PORT="network"` in the mnist env files |
| Missing `tensorflow` or `scikit-learn` errors | `pip3 install tensorflow scikit-learn` in your venv |
| `docker-compose` command fails | Install the latest version via `brew install docker-compose` |
| `mnist_fl` database not visible in `get databases` | Manually connect: `connect dbms mnist_fl where type = psql and user = demo and password = passwd and ip = 127.0.0.1 and port = 5432 and memory = true` |
