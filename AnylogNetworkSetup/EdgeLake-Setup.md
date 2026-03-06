# EdgeLake Setup Guide (Apple Silicon)

This is the **alternative method** using EdgeLake (open-source) instead of AnyLog. For the primary AnyLog method, see [AnyLog-Setup.md](./AnyLog-Setup.md).

EdgeLake does not require a license key but uses Docker bridge networking, so you must discover container IPs and update config files accordingly.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [PostgreSQL Setup](#2-postgresql-setup)
3. [Pull the EdgeLake Image](#3-pull-the-edgelake-image)
4. [Makefile Configuration](#4-makefile-configuration)
5. [Start the Master Node](#5-start-the-master-node)
6. [Discover Container IPs](#6-discover-container-ips)
7. [Configure Operator Env Files](#7-configure-operator-env-files)
8. [Start Operator Nodes](#8-start-operator-nodes)
9. [Validate the Network](#9-validate-the-network)
10. [EdgeFL Environment Setup](#10-edgefl-environment-setup)
11. [Insert MNIST Data](#11-insert-mnist-data)
12. [Run Training](#12-run-training)
13. [Inference](#13-inference)
14. [Quick Start (Returning Users)](#14-quick-start-returning-users)
15. [Cleanup](#15-cleanup)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Prerequisites

- **Docker Desktop** — installed and running
- **Python 3.10+** with `venv` support
- **`envsubst`** — typically included with `gettext` (`brew install gettext`)

No license key is required for EdgeLake.

---

## 2. PostgreSQL Setup

From the EdgeFL repo:

```bash
cd EdgeLake/postgres

make up NAME=postgres1 HOST_PORT=5432 VOLUME=pgdata1
make up NAME=postgres2 HOST_PORT=5433 VOLUME=pgdata2
make up NAME=postgres3 HOST_PORT=5434 VOLUME=pgdata3
```

Default credentials (from the Makefile): user=`demo`, password=`passwd`, database=`mnist_fl`.

---

## 3. Pull the EdgeLake Image

Pull the image ahead of time so deploys are fast:

```bash
docker pull anylogco/edgelake:latest
```

### Prevent image removal on cleanup

In `EdgeLake/Makefile`, the `clean` target uses `--rmi all` by default, which removes all images. If you want to keep the pulled image between runs, remove the `--rmi all` flag from the `clean` target.

---

## 4. Makefile Configuration

In `EdgeLake/Makefile`, the ARM64 tag override should be **commented out** so that `TAG=latest` is used (the `latest` tag already includes ARM64 support):

```makefile
export TAG := latest
# ifeq ($(ARCH),aarch64)
#     export TAG := latest-arm64
# else ifeq ($(ARCH),arm64)
#     export TAG := latest-arm64
# endif
```

Also ensure each EdgeLake env file (`EdgeLake/docker_makefile/edgelake_*.env`) contains:

```env
INIT_TYPE=prod
```

The `TAG` is already set by the Makefile, so it does not need to be in the env files.

---

## 5. Start the Master Node

From `EdgeLake/`:

```bash
make up EDGELAKE_TYPE=master TAG=latest \
  EDGELAKE_SERVER_PORT=32048 EDGELAKE_REST_PORT=32049 NODE_NAME=master
```

Wait ~30 seconds for the node to initialize.

---

## 6. Discover Container IPs

EdgeLake uses Docker bridge networking, so you must find the internal IPs of each container.

### Master IP

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' master
```

Example output: `172.17.0.2`

### PostgreSQL IPs

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres1
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres2
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres3
```

Example outputs: `172.18.0.2`, `172.18.0.3`, `172.18.0.4`

> **Write these IPs down** — you will use them in the next step.

---

## 7. Configure Operator Env Files

All env files are in `EdgeLake/docker_makefile/`.

### 7a. Set `LEDGER_CONN` (all files)

Set `LEDGER_CONN` to the **master's Docker IP** and TCP port in **all four** env files:

| File                       | Value (example)             |
|----------------------------|-----------------------------|
| `edgelake_master.env`      | `LEDGER_CONN=172.17.0.2:32048` |
| `edgelake_operator1.env`   | `LEDGER_CONN=172.17.0.2:32048` |
| `edgelake_operator2.env`   | `LEDGER_CONN=172.17.0.2:32048` |
| `edgelake_operator3.env`   | `LEDGER_CONN=172.17.0.2:32048` |

> **Important:** The master env file must also have `LEDGER_CONN` set, otherwise you will see `Metadata without network peers` errors.

### 7b. Set `DB_IP` (operator files only)

Map each operator to its corresponding PostgreSQL container IP:

| File                       | `DB_IP` (example)   |
|----------------------------|---------------------|
| `edgelake_operator1.env`   | `172.18.0.2` (postgres1) |
| `edgelake_operator2.env`   | `172.18.0.3` (postgres2) |
| `edgelake_operator3.env`   | `172.18.0.4` (postgres3) |

### 7c. Set `DB_PORT` (operator files)

All operators should use port `5432` (the **internal** container port), not the host-mapped ports:

```env
DB_PORT=5432
```

> **Why:** EdgeLake containers communicate with PostgreSQL over Docker's internal network, so they use the container's internal port (`5432`), not the host-mapped ports (`5432`/`5433`/`5434`).

### 7d. Operator port assignments

Each operator env file should have unique ports:

| File                       | `ANYLOG_SERVER_PORT` | `ANYLOG_REST_PORT` |
|----------------------------|---------------------|--------------------|
| `edgelake_operator1.env`   | `32148`             | `32149`            |
| `edgelake_operator2.env`   | `32248`             | `32249`            |
| `edgelake_operator3.env`   | `32348`             | `32349`            |

### 7e. Disable NoSQL/Blobs (if present)

Comment out or set to `false`:

```env
#ENABLE_NOSQL=false
#BLOBS_DBMS=false
#BLOBS_STORAGE=false
```

---

## 8. Start Operator Nodes

From `EdgeLake/`:

```bash
make up EDGELAKE_TYPE=operator TAG=latest \
  EDGELAKE_SERVER_PORT=32148 EDGELAKE_REST_PORT=32149 NODE_NAME=operator1

make up EDGELAKE_TYPE=operator TAG=latest \
  EDGELAKE_SERVER_PORT=32248 EDGELAKE_REST_PORT=32249 NODE_NAME=operator2

make up EDGELAKE_TYPE=operator TAG=latest \
  EDGELAKE_SERVER_PORT=32348 EDGELAKE_REST_PORT=32349 NODE_NAME=operator3
```

Wait ~30 seconds for each node to initialize.

---

## 9. Validate the Network

### 9a. Master node

```bash
docker attach master
# Press Enter a few times, then type:
test network
```

Expected:

```
Address          Node Type Node Name Status
----------------|---------|---------|------|
172.17.0.2:32048|master   |master   |  +   |
```

Detach with `Ctrl+P`, `Ctrl+Q`.

### 9b. Full network (from any operator)

```bash
docker attach operator1
# Press Enter, then:
test network
```

Expected — all four nodes with `+`:

```
Address          Node Type Node Name Status
----------------|---------|---------|------|
172.17.0.2:32048|master   |master   |  +   |
172.17.0.3:32148|operator |operator1|  +   |
172.17.0.4:32248|operator |operator2|  +   |
172.17.0.5:32348|operator |operator3|  +   |
```

### 9c. Check databases

```
get databases
```

Expected (on an operator):

```
Active DBMS Connections
Logical DBMS Database Type Owner  IP:Port         Configuration                                     Storage    
------------|-------------|------|---------------|--------------------------------------------------|----------|
almgm       |psql         |system|172.18.0.2:5432|Autocommit On, Fsync on                           |Persistent|
mnist_fl    |psql         |user  |172.18.0.2:5432|Autocommit Off, Fsync on                          |Persistent|
system_query|sqlite       |system|Local          |Autocommit On, RAM, Fsync full (after each write) |MEMORY     |
```

If `mnist_fl` is missing, manually connect it:

```
connect dbms mnist_fl where type = psql and user = demo and password = passwd and ip = <postgres_ip> and port = 5432 and memory = true
```

---

## 10. EdgeFL Environment Setup

### 10a. Python environment

```bash
cd /path/to/EdgeFL
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
pip3 install torch torchvision requests tensorflow scikit-learn dotenv "python-dotenv[cli]" uvicorn fastapi docker requests_toolbelt
```

### 10b. Configure EdgeFL env files

Edit the files in `edgefl/env_files/mnist/`. Set `GITHUB_DIR` to your EdgeFL repo path in each file.

Port mappings (using `127.0.0.1` since ports are forwarded to the host):

| File           | `EXTERNAL_IP` (REST)  | `EXTERNAL_TCP_IP_PORT` (TCP) |
|----------------|----------------------|------------------------------|
| `mnist-agg.env`| `127.0.0.1:32049`    | `127.0.0.1:32048`            |
| `mnist1.env`   | `127.0.0.1:32149`    | `127.0.0.1:32148`            |
| `mnist2.env`   | `127.0.0.1:32249`    | `127.0.0.1:32248`            |
| `mnist3.env`   | `127.0.0.1:32349`    | `127.0.0.1:32348`            |

> **Note:** If you encounter SQL query connection errors, try setting `EXTERNAL_TCP_IP_PORT="network"` instead.

Make sure all env files use the same data handler (`MODULE_NAME=MnistDataHandler`, `MODULE_FILE=custom_data_handler.py` or `MODULE_NAME=MnistDataHandler`, `MODULE_FILE=mnist_data_handler.py`).

---

## 11. Insert MNIST Data

### 11a. Fix `store_data.py` (if needed)

In `edgefl/data/mnist/store_data.py`, change the two instances of:

```python
"image": img.numpy().flatten().tolist(),
```

to:

```python
"image": json.dumps(img.numpy().flatten().tolist()),
```

### 11b. Insert data

```bash
cd edgefl/data/mnist

python3 store_data.py 127.0.0.1:32149 --db-name mnist_fl
python3 store_data.py 127.0.0.1:32249 --db-name mnist_fl
python3 store_data.py 127.0.0.1:32349 --db-name mnist_fl
```

### 11c. Validate

Attach to any operator and verify:

```
blockchain get table
# Should show mnist_train and mnist_test

get tables where dbms = mnist_fl
# Should list mnist_train and mnist_test with V under Local DBMS

get data nodes
# Should show all three operators hosting both tables

get streaming
# Should show rows ingested for mnist_train and mnist_test
```

---

## 12. Run Training

Open **4 terminal windows**, each with the venv activated. All commands run from `edgefl/`.

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

### Initialize

These steps can also be done through the GUI (see [Section 14](#14-web-gui-optional-but-recommended)).

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

### Start training

```bash
curl -X POST http://localhost:8080/start-training \
  -H "Content-Type: application/json" \
  -d '{
    "totalRounds": 10,
    "minParams": 3,
    "index": "test-index"
  }'
```

---

## 13. Inference

```bash
curl -X POST http://localhost:8081/inference/test-index
curl -X POST http://localhost:8082/inference/test-index
curl -X POST http://localhost:8083/inference/test-index
```

---

## 14. Web GUI (Optional but Recommended)

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

## 15. Quick Start (Returning Users)

> Assumes all configuration is already done.

### Start infrastructure

```bash
# PostgreSQL
cd EdgeLake/postgres
make up NAME=postgres1 HOST_PORT=5432 VOLUME=pgdata1
make up NAME=postgres2 HOST_PORT=5433 VOLUME=pgdata2
make up NAME=postgres3 HOST_PORT=5434 VOLUME=pgdata3

# EdgeLake nodes
cd ../
make up EDGELAKE_TYPE=master TAG=latest EDGELAKE_SERVER_PORT=32048 EDGELAKE_REST_PORT=32049 NODE_NAME=master
make up EDGELAKE_TYPE=operator TAG=latest EDGELAKE_SERVER_PORT=32148 EDGELAKE_REST_PORT=32149 NODE_NAME=operator1
make up EDGELAKE_TYPE=operator TAG=latest EDGELAKE_SERVER_PORT=32248 EDGELAKE_REST_PORT=32249 NODE_NAME=operator2
make up EDGELAKE_TYPE=operator TAG=latest EDGELAKE_SERVER_PORT=32348 EDGELAKE_REST_PORT=32349 NODE_NAME=operator3
```

### Verify IPs (update env files if changed)

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' master
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres1
```

> **Important:** Docker may assign different IPs on restart. Always re-check container IPs and update `LEDGER_CONN` and `DB_IP` if they changed.

### Insert data

```bash
cd ../../EdgeFL
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

## 16. Cleanup

### Stop EdgeLake nodes (from `EdgeLake/`)

```bash
make clean EDGELAKE_TYPE=master TAG=latest \
  EDGELAKE_SERVER_PORT=32048 EDGELAKE_REST_PORT=32049 NODE_NAME=master

make clean EDGELAKE_TYPE=operator TAG=latest \
  EDGELAKE_SERVER_PORT=32148 EDGELAKE_REST_PORT=32149 NODE_NAME=operator1

make clean EDGELAKE_TYPE=operator TAG=latest \
  EDGELAKE_SERVER_PORT=32248 EDGELAKE_REST_PORT=32249 NODE_NAME=operator2

make clean EDGELAKE_TYPE=operator TAG=latest \
  EDGELAKE_SERVER_PORT=32348 EDGELAKE_REST_PORT=32349 NODE_NAME=operator3
```

### Stop PostgreSQL (from `EdgeLake/postgres/`)

```bash
cd postgres/
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

## 17. Troubleshooting

| Problem | Solution |
|---------|----------|
| `Metadata without network peers` on master | Add `LEDGER_CONN=<master_docker_ip>:32048` to `edgelake_master.env` |
| `Database connect error: mnist_fl using psql failed to connect` on operator2/3 | Set `DB_PORT=5432` in all operator env files (use internal port, not host port) |
| Container IPs changed after restart | Re-run `docker inspect` and update `LEDGER_CONN` and `DB_IP` in all env files |
| `TypeError: expected string or bytes-like object, got 'list'` in `store_data.py` | Wrap image list with `json.dumps()` (see [Section 11a](#11a-fix-store_datapyif-needed)) |
| SQL query connection error from EdgeFL nodes | Set `EXTERNAL_TCP_IP_PORT="network"` in the mnist env files |
| Missing `tensorflow` or `scikit-learn` | `pip3 install tensorflow scikit-learn` in your venv |
| `mnist_fl` database not visible | Manually connect inside the operator shell (see [Section 9c](#9c-check-databases)) |
| ARM64 image issues | Ensure `TAG=latest` in the Makefile and that the ARM override lines are commented out |
