# MNIST Dataset Demo
The MNIST dataset (Modified National Institute of Standards and Technology) is a large collection of handwritten digits (0–9). It contains 60,000 training images and 10,000 test images, each being a grayscale image of size 28x28 pixels. The dataset is widely used in the machine learning community as a benchmark for image classification tasks, because it is simple yet challenging enough to demonstrate the power of algorithms.

The goal of this demo is to use Federated Learning approach to train a machine learning model
on recognizing digits from handwritten images. The data in the demo is preprocessed. 

# Demo execution
To run the MNIST dataset with 3 training nodes and 1 aggregator node,
make sure you have 3 EdgeLake operators and 1 EdgeLake master node deployed.
We will assume a 4 node setup, but it is easy to modify this example to 
add additional training nodes.

## Define env files
You will need to define in the `edgefl/env_files/mnist` directory. 
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

We now need to update the env files in the `edgefl/env_files/mnist/` directory. To do this, we need to update
the listed variables in the following files `mnist-agg.env`, `mnist1.env`, `mnist2.env`, `mnist3.env` with the inet IP (e.g., `192.1.1.1`):
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

Note that `mnist-agg.env` requires fewer fields, so fill in the existing ones.


## Insert data to the EdgeLake operator nodes

Note that needs to be done each time you reset your EdgeLake operator cluster. 
Executing the script below will insert data into the EdgeLake operator's respective database.  
in the `mnist_fl` database. Do this for each operator, changing the IP and port respectively.
```bash
cd edgefl/data/mnist
python3 store_data.py [inet_ip]:[rest-port] --db-name mnist_fl # operator1
python3 store_data.py [inet_ip]:[rest-port] --db-name mnist_fl # operator2
python3 store_data.py [inet_ip]:[rest-port] --db-name mnist_fl # operator3 
```

If you want to train on more (or less) data edit lines `153` and `154` in `edgefl/data/mnist/mnist_db_script.py`.
Moreover, if you'd like to train over more than 10 rounds, edit line `152`. 
Note that training on more data will result in a model with higher accuracy at the model inference step below.
```bash
python3 store_data.py [inet_ip]:[rest-port] --db-name mnist_fl --num-rounds 10 --num-rows 50
```

## Validate data is stored correctly
```bash
docker attach operator2
AL operator2 +> blockchain get table

[{'table' : {'name' : 'mnist_train',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS mnist_train(  row_id SERIAL PRIMARY K'
                        'EY,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  tsd_nam'
                        'e CHAR(3),  tsd_id INT,  image varchar,  label int,  round_numbe'
                        'r int ); CREATE INDEX mnist_train_tsd_index ON mnist_train(tsd_n'
                        'ame, tsd_id); CREATE INDEX mnist_train_insert_timestamp_index ON'
                        ' mnist_train(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : 'a2608721de0b7a02cee9c354fa6774dc',
             'date' : '2025-08-19T15:12:53.861249Z',
             'ledger' : 'global'}},
 {'table' : {'name' : 'mnist_test',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS mnist_test(  row_id SERIAL PRIMARY KE'
                        'Y,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  tsd_name'
                        ' CHAR(3),  tsd_id INT,  image varchar,  label int,  round_number'
                        ' int ); CREATE INDEX mnist_test_tsd_index ON mnist_test(tsd_name'
                        ', tsd_id); CREATE INDEX mnist_test_insert_timestamp_index ON mni'
                        'st_test(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : 'f677a69bb214a3e73ac9e2e260e8b44b',
             'date' : '2025-08-19T15:12:53.916385Z',
             'ledger' : 'global'}},
 ]
```

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
  "index": "test-index"
}'
```
After, start the training process. Note that the `index` needs to align with the above. 
```bash
curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 10,
  "minParams": 3,
  "index": "test-index"
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
  "index": "test-index"
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
  "index": "test-index"
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
   "index": "test-index"
 }'
 ```

## Inference

At any point, you can execute edge inference directly on the node.
This can be done on each training node. The output will be the accuracy based on the local test data
held out from training. Note that this is defined based on the provided data handler. Please look
at the data handler template for more information. 
```bash
curl -X POST http://localhost:8081/inference/test-index
curl -X POST http://localhost:8082/inference/test-index
curl -X POST http://localhost:8083/inference/test-index
```

An example output looks like this:
```bash
curl -X POST http://localhost:8081/inference/test-index ; curl -X POST http://localhost:8082/inference/test-index ; curl -X POST http://localhost:8083/inference/test-index 
{"index":"test-index","message":"Inference completed successfully","model_accuracy":"92.0","status":"success"}
{"index":"test-index","message":"Inference completed successfully","model_accuracy":"88.0","status":"success"}
{"index":"test-index","message":"Inference completed successfully","model_accuracy":"86.0","status":"success"}
```

You can also do a direct inference on the aggregator which requires inputting test data and its test
labels (i.e. expected predictions). The label must correspond to the given input and will be used to
compare against the actual predictions of the model's testing output. The data type of the test data
can be anything as long as fits the data type of the dataset. Below is an example for MNIST:
```bash
curl -X POST http://localhost:8080/infer \
-H "Content-Type: application/json" \
-d '{
  "input": [
    [28x28 array]
  ],
  "index": "test-index
}'
```

This will output a prediction. 