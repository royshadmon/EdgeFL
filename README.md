# EdgeLake Project

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

- Python 3.11 (currently doesn't work with 3.12)
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

    Note that there are currently two datasets in `blockchain/data`: _mnist_ and _winniio_.
    For this setup, we will use the winniio dataset and configure for it.

    - Navigate to `Anylog-Edgelake-CSE115D/blockchain/env_files`

   ```bash
   cd Anylog-Edgelake-CSE115D/blockchain/env_files
   ```

    - Locate `winniio.env` in the directory
    - Modify these variables in the file:

        - `EXTERNAL_IP`: Replace the IP portion with your machine's IP address.
                You can fetch them in the terminal using the command `ifconfig` on
                Mac/Linux, found under `inet`/`en0`(`ipconfig` on Windows under `IPv4`).
        - `EXTERNAL_TCP_IP_PORT`: Do the same process done for `EXTERNAL_IP`.
        - `PSQL_DB_USER`: Set this to the user for the database that will be used.
        - `PSQL_DB_PASSWORD`: If you have a password for the user, set this to it.
        - `FILE_WRITE_DESTINATION`: Set this path to `[/path/to]/Anylog-Edgelake-CSE115D/blockchain/file_write`

    - Notes:
    
        - If your database will not be locally hosted, set `PSQL_DB_HOST` accordingly.
        - If you have specified the port of your database, set `PSQL_DB_PORT` accordingly.

3. Install pip:

    - Navigate back to `Anylog-Edgelake-CSE115D/` and run the following:

   ```
   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
   python3.11 get-pip.py
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   pip install flask[async]
   ```

5. Set up and start a Postgres instance

    - [Postgres Mac instructions](https://www.sqlshack.com/setting-up-a-postgresql-database-on-mac/)

6. Set up and load data into Postgres

    - In `Anylog-Edgelake-CSE115D/`, navigate to `blockchain/data/winniio-rooms/linode-setup/`
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
            `blockchain/platform_components/aggregator/` and
            `blockchain/platform_components/node/`, respectively.
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

### Model definitions
To train on the MNIST dataset, set "model_def: 1." \
To train on the Winniio dataset, set "model_def: 2."

Note that you need to also update the `blockchain/env_files/mnist.env` or `blockchain/env_files/winniio.env` files + initialize them before starting the node/aggregator server.

## Custom Data Handler
(Documentation for creating custom data handler (needs to be finished). Examples
of working data handlers can be found in the directory `blockchain/platform_components/data_handlers`)

## Starting the Training Process

To begin the training process for the MNIST/Winniio dataset, use this curl command:

```bash
curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5,
  "minParams": 1
}'
```

## Running inference once the model is trained

In the following command, you can specify the port in the URL to run inference
on specific nodes:

```bash
curl -X POST http://localhost:8081/inference
```

## Shutting Down the Servers

~~When you're done, you can stop all running servers using:~~ \
The following script has not yet been updated (eventually):
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