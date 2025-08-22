# Chest-Xray Bounding Box Demo


- Ensure that the kaggle package is installed via requirements.txt
- Go to [Kaggle](kaggle.com) and create/sign-in to your Kaggle account
- Go to your account settings
- Scroll down to PAI and "create new token" and download the JSON
- Add the json to /home/{user}/.config/kaggle/kaggle.json


# Demo execution
To train on the Winniio dataset with 3 training nodes and 1 aggregator node,
make sure you have 3 EdgeLake operators and 1 EdgeLake master node deployed.
We will assume a 4 node setup, but it is easy to modify this example to 
add additional training nodes.

## Define env files
You will need to define in the `edgefl/env_files/chest_xrays_bbox/` directory. 
Each env file will be used by one of the training nodes. This file
provides the nodes the necessary, custom information needed to execute
the training and aggregation process.

For each EdgeLake node run the `get connections` command to get the nodes ports.
```bash
AL operator1 +> get connections

Type      External Address    Internal Address    Bind Address
---------|-------------------|-------------------|----------------|
TCP      |172.18.0.4:32248   |172.18.0.4:32248   |172.18.0.4:32248|
REST     |104.60.100.77:32249|104.60.100.77:32249|0.0.0.0:32249   |
Messaging|Not declared       |Not declared       |Not declared    |
```

We now need to update the env files in the `edgefl/env_files/chest_xrays_bbox/` directory. To do this, we need to update
the listed variables in the following files `chest_xrays_bbox-agg.env`, `chest_xrays_bbox1.env`, `chest_xrays_bbox2.env`, `chest_xrays_bbox3.env` with the inet IP (e.g., `192.1.1.1`):
- `GITHUB_DIR` --> the path to the EdgeFL repo
- `TRAINING_APPLICATION` --> the path to the training logic file
- `MODULE_NAME` --> the training file class name
- `MODULE_FILE` --> the training filename
- `EXTERNAL_IP` --> e.g., [inet_ip]:32249
- `EXTERNAL_TCP_IP_PORT` --> e.g., [inet_ip]:32248
- `LOGICAL_DATABASE` --> e.g., mnist_fl
- `TRAIN_TABLE` --> the EdgeLake table for the training data 
- `TEST_TABLE` --> the EdgeLake table for the test data
- `EDGELAKE_DOCKER_CONTAINER_NAME` --> the EdgeLake container name

Note that `chest_xrays_bbox-agg.env` requires fewer fields, so fill in the existing ones.


## Insert data to the EdgeLake operator nodes

Note that needs to be done each time you reset your EdgeLake operator cluster. 
Executing the script below will insert data into the EdgeLake operator's respective database.  
in the `mnist_fl` database. Do this for each operator, changing the IP and port respectively.
```bash
cd edgefl/data/chest_xrays_bbox/
python3 chest_xrays_bbox_db_script.py [inet_ip]:[rest-port] --db-name mnist_fl # operator1
python3 chest_xrays_bbox_db_script.py [inet_ip]:[rest-port] --db-name mnist_fl # operator2
python3 chest_xrays_bbox_db_script.py [inet_ip]:[rest-port] --db-name mnist_fl # operator3
```

## Validate data is stored correctly
```bash
docker attach operator2
AL operator2 +> blockchain get table

[{'table' : {'name' : 'xray_test',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS xray_test(  row_id SERIAL PRIMARY KEY'
                        ',  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  tsd_name '
                        'CHAR(3),  tsd_id INT,  filename varchar,  width int,  height int'
                        ',  class varchar,  x_min float,  y_min float,  x_max float,  y_m'
                        'ax float,  round_number int ); CREATE INDEX xray_test_tsd_index '
                        'ON xray_test(tsd_name, tsd_id); CREATE INDEX xray_test_insert_ti'
                        'mestamp_index ON xray_test(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : '3f9294a93b8e47abc319a9f4f894690d',
             'date' : '2025-08-22T17:58:54.341516Z',
             'ledger' : 'global'}},
 {'table' : {'name' : 'xray_train',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS xray_train(  row_id SERIAL PRIMARY KE'
                        'Y,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  tsd_name'
                        ' CHAR(3),  tsd_id INT,  filename varchar,  width int,  height in'
                        't,  class varchar,  x_min float,  y_min float,  x_max float,  y_'
                        'max float,  round_number int ); CREATE INDEX xray_train_tsd_inde'
                        'x ON xray_train(tsd_name, tsd_id); CREATE INDEX xray_train_inser'
                        't_timestamp_index ON xray_train(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : '0731e300b0a19cb585ec41b9ad5f0305',
             'date' : '2025-08-22T17:58:54.376247Z',
             'ledger' : 'global'}}]
```

Now that data is loaded into the database continue to the next step.

## Starting aggregator and training nodes
Note to execute the below commands in a new terminal. 
```bash
cd edgefl
dotenv -f env_files/chest_xrays_bbox/chest_xrays_bbox-agg.env run -- uvicorn platform_components.aggregator.aggregator_server:app --host 0.0.0.0 --port 8080
dotenv -f env_files/chest_xrays_bbox/chest_xrays_bbox1.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8081
dotenv -f env_files/chest_xrays_bbox/chest_xrays_bbox2.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8082
dotenv -f env_files/chest_xrays_bbox/chest_xrays_bbox3.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8083
```

Once all the nodes are running. We can start the training process. Note that you can view the 
predefined training application file here: `edgefl/platform_components/data_handlers/chest_xrays_bbox_data_handler.py`.

## Initialize model parameters and training application and start training
Execute the following `curl` command to initialize training. As a result of this command,
each of the training nodes should be printing out a set of model weights to the screen.
If you do not see this, then your data connector is correctly set up. Please see the resolving
common issues section below.

To initialize training execute the following CURL request to the aggregator node.
Note that you need to specify each nodeURL for which you want to participate in the
training process. 
The `index` is a unique identifier. 
```bash
curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8081",
    "http://localhost:8082",
    "http://localhost:8083"
  ],
  "index": "bbox-fl"
}'
```
After, start the training process. Note that the `index` needs to align with the above. 
```bash
curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5,
  "minParams": 3,
  "index": "bbox-fl"
}'
```

`totalRounds` defines how many continuous rounds to train for. `minParams` defines how many parameters
the aggregator should wait for before starting the next round.

### Adding additional training nodes dynamically
At any point during the training process, you can add additional nodes to the process by calling initialization again on the new nodes 
(must use the same `index`) and `minParams` will be dynamically adjusted as necessary.
```bash
curl -X POST http://localhost:8080/init \
-H "Content-Type: application/json" \
-d '{
  "nodeUrls": [
    "http://localhost:8084"
  ],
  "index": "bbox-fl"
}'
```

### Updating minParams

`minParams` is the number of model weights the aggregator waits for before aggregating 
the model weights and starting a new round. This can be updated at anytime after initialization. 
The specified `index` must exist in order to update `minParams`.
```bash
curl -X POST http://localhost:8080/update-minParams \
-H "Content-Type: application/json" \
-d '{
  "updatedMinParams": 3,
  "index": "bbox-fl"
}'
```

### Extending the number of training rounds

Once the training process is complete, you may choose to do additional rounds of training on the same model.
Note that (based on the queries), you need to have the data / query structure to support this. 
```bash
curl -X POST http://localhost:8080/continue-training \
 -H "Content-Type: application/json" \
 -d '{
   "additionalRounds": 3, 
   "minParams": 4,
   "index": "bbox-fl"
 }'
 ```

## Inference

At any point, you can execute edge inference directly on the node.
This can be done on each training node. The output will be the accuracy based on the local test data
held out from training. Note that this is defined based on the provided data handler. Please look
at the data handler template for more information. 
```bash
curl -X POST http://localhost:8081/inference/bbox-fl
curl -X POST http://localhost:8082/inference/bbox-fl
curl -X POST http://localhost:8083/inference/bbox-fl
```

An example output looks like this:
```bash
curl -X POST http://localhost:8081/inference/bbox-fl ; curl -X POST http://localhost:8082/inference/bbox-fl ; curl -X POST http://localhost:8083/inference/bbox-fl 
{'index': 'bbox-fl', 'status': 'success', 'message': 'Inference completed successfully', 'model_accuracy': '10.0'}
{'index': 'bbox-fl', 'status': 'success', 'message': 'Inference completed successfully', 'model_accuracy': '40.0'}
{'index': 'bbox-fl', 'status': 'success', 'message': 'Inference completed successfully', 'model_accuracy': '5.0'}
```

Note that direct inference is not supported for this demo,
but it would be a great contribution!

