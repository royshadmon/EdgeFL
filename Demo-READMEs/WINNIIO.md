# WINNIIO Dataset Demo
The Winniio dataset was provided by our partners at [Winnio](https://www.bing.com/search?q=winniio).
This dataset contains various telemetry data generated from rooms in Sweden
used to build AI models to optimize HVAC usage. 

The goal of this demo is to use Federated Learning approach to train a machine learning model
on inferring temperature predictions for rooms. The data in the demo is preprocessed and can
be viewed in the `edgefl/data/winniio-rooms/` directory. 


# Demo execution
To train on the Winniio dataset with 3 training nodes and 1 aggregator node,
make sure you have 3 EdgeLake operators and 1 EdgeLake master node deployed.
We will assume a 4 node setup, but it is easy to modify this example to 
add additional training nodes.

## Define env files
You will need to define in the `edgefl/env_files/winniio` directory. 
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

We now need to update the env files in the `edgefl/env_files/winniio/` directory. To do this, we need to update
the listed variables in the following files `winniio-agg.env`, `winniio1.env`, `winniio2.env`, `winniio3.env` with the inet IP (e.g., `192.1.1.1`):
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
cd edgefl/data/winniio-rooms/
python3 publish_data.py [inet_ip]:[rest-port] room_12004.csv --db-name mnist_fl # operator1
python3 publish_data.py [inet_ip]:[rest-port] room_12055.csv --db-name mnist_fl # operator2
python3 publish_data.py [inet_ip]:[rest-port] room_12090.csv --db-name mnist_fl # operator3
```

## Validate data is stored correctly
```bash
docker attach operator2
AL operator2 +> blockchain get table

[{'table' : {'name' : 'room_12004_train',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS room_12004_train(  row_id SERIAL PRIM'
                        'ARY KEY,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  ts'
                        'd_name CHAR(3),  tsd_id INT,  actuatorstate float,  co2value flo'
                        'at,  eventcount float,  humidity float,  temperature float,  swi'
                        'tchstatus float,  day int,  time float,  month int,  date int,  '
                        'label float,  round_number int,  data_type char(5) ); CREATE IND'
                        'EX room_12004_train_tsd_index ON room_12004_train(tsd_name, tsd_'
                        'id); CREATE INDEX room_12004_train_insert_timestamp_index ON roo'
                        'm_12004_train(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : '8e44129bbd6069b0aa514013d536cf79',
             'date' : '2025-08-19T18:09:40.039949Z',
             'ledger' : 'global'}},
 {'table' : {'name' : 'room_12004_test',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS room_12004_test(  row_id SERIAL PRIMA'
                        'RY KEY,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  tsd'
                        '_name CHAR(3),  tsd_id INT,  actuatorstate float,  co2value floa'
                        't,  eventcount float,  humidity float,  temperature float,  swit'
                        'chstatus float,  day int,  time float,  month int,  date int,  l'
                        'abel float,  round_number int,  data_type char(4) ); CREATE INDE'
                        'X room_12004_test_tsd_index ON room_12004_test(tsd_name, tsd_id)'
                        '; CREATE INDEX room_12004_test_insert_timestamp_index ON room_12'
                        '004_test(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : 'c0875cd02157c2e360a56fb22fd07cf4',
             'date' : '2025-08-19T18:09:40.145374Z',
             'ledger' : 'global'}},
 {'table' : {'name' : 'room_12055_train',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS room_12055_train(  row_id SERIAL PRIM'
                        'ARY KEY,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  ts'
                        'd_name CHAR(3),  tsd_id INT,  actuatorstate float,  co2value flo'
                        'at,  eventcount float,  humidity float,  temperature float,  swi'
                        'tchstatus float,  day int,  time float,  month int,  date int,  '
                        'label float,  round_number int,  data_type char(5) ); CREATE IND'
                        'EX room_12055_train_tsd_index ON room_12055_train(tsd_name, tsd_'
                        'id); CREATE INDEX room_12055_train_insert_timestamp_index ON roo'
                        'm_12055_train(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : '671f0822967f135cd0d558cd2c0fe3aa',
             'date' : '2025-08-19T18:09:44.880070Z',
             'ledger' : 'global'}},
 {'table' : {'name' : 'room_12055_test',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS room_12055_test(  row_id SERIAL PRIMA'
                        'RY KEY,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  tsd'
                        '_name CHAR(3),  tsd_id INT,  actuatorstate float,  co2value floa'
                        't,  eventcount float,  humidity float,  temperature float,  swit'
                        'chstatus float,  day int,  time float,  month int,  date int,  l'
                        'abel float,  round_number int,  data_type char(4) ); CREATE INDE'
                        'X room_12055_test_tsd_index ON room_12055_test(tsd_name, tsd_id)'
                        '; CREATE INDEX room_12055_test_insert_timestamp_index ON room_12'
                        '055_test(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : '05e7b23162d4e5d87899b7a5ca25efe9',
             'date' : '2025-08-19T18:09:44.935022Z',
             'ledger' : 'global'}},
 {'table' : {'name' : 'room_12090_train',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS room_12090_train(  row_id SERIAL PRIM'
                        'ARY KEY,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  ts'
                        'd_name CHAR(3),  tsd_id INT,  actuatorstate float,  co2value flo'
                        'at,  eventcount float,  humidity float,  temperature float,  swi'
                        'tchstatus float,  day int,  time float,  month int,  date int,  '
                        'label float,  round_number int,  data_type char(5) ); CREATE IND'
                        'EX room_12090_train_tsd_index ON room_12090_train(tsd_name, tsd_'
                        'id); CREATE INDEX room_12090_train_insert_timestamp_index ON roo'
                        'm_12090_train(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : '8733a3c957991a68d83ebca2712ec346',
             'date' : '2025-08-19T18:09:50.551014Z',
             'ledger' : 'global'}},
 {'table' : {'name' : 'room_12090_test',
             'dbms' : 'mnist_fl',
             'create' : 'CREATE TABLE IF NOT EXISTS room_12090_test(  row_id SERIAL PRIMA'
                        'RY KEY,  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  tsd'
                        '_name CHAR(3),  tsd_id INT,  actuatorstate float,  co2value floa'
                        't,  eventcount float,  humidity float,  temperature float,  swit'
                        'chstatus float,  day int,  time float,  month int,  date int,  l'
                        'abel float,  round_number int,  data_type char(4) ); CREATE INDE'
                        'X room_12090_test_tsd_index ON room_12090_test(tsd_name, tsd_id)'
                        '; CREATE INDEX room_12090_test_insert_timestamp_index ON room_12'
                        '090_test(insert_timestamp);',
             'source' : 'Processing JSON file',
             'id' : 'fed10db28a1d47e354a843b1e2159ee7',
             'date' : '2025-08-19T18:09:50.616423Z',
             'ledger' : 'global'}}]
```

Now that data is loaded into the database continue to the next step.

## Starting aggregator and training nodes
Note to execute the below commands in a new terminal. 
```bash
cd edgefl
dotenv -f env_files/mnist/winniio-agg.env run -- uvicorn platform_components.aggregator.aggregator_server:app --host 0.0.0.0 --port 8080
dotenv -f env_files/mnist/winniio1.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8081
dotenv -f env_files/mnist/winniio2.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8082
dotenv -f env_files/mnist/winniio3.env run -- uvicorn platform_components.node.node_server:app --host 0.0.0.0 --port 8083
```

Once all the nodes are running. We can start the training process. Note that you can view the 
predefined training application file here: `edgefl/platform_components/data_handlers/winniio_data_handler.py`.

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
  "index": "winniio-fl"
}'
```
After, start the training process. Note that the `index` needs to align with the above. 
```bash
curl -X POST http://localhost:8080/start-training \
-H "Content-Type: application/json" \
-d '{
  "totalRounds": 5,
  "minParams": 3,
  "index": "winniio-fl"
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
  "index": "winniio-fl"
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
  "index": "winniio-fl"
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
curl -X POST http://localhost:8081/inference/fl-winniio
curl -X POST http://localhost:8082/inference/fl-winniio
curl -X POST http://localhost:8083/inference/fl-winniio
```

An example output looks like this:
```bash
curl -X POST http://localhost:8081/inference/test-index ; curl -X POST http://localhost:8082/inference/test-index ; curl -X POST http://localhost:8083/inference/test-index ; curl -X POST http://localhost:8084/inference/test-index
{'index': 'fl-winniio', 'status': 'success', 'message': 'Inference completed successfully', 'model_accuracy': '{'results': "{1: '20.82636833190918 --> 22.786666870117188', 2: '21.368873596191406 --> 20.889999389648438', 3: '22.273048400878906 --> 21.760000228881836', 4: '21.30950164794922 --> 25.989999771118164', 5: '18.67854118347168 --> 22.270000457763672', 6: '21.018421173095703 --> 21.670000076293945', 7: '22.944976806640625 --> 21.79199981689453', 8: '24.351228713989258 --> 22.360000610351562', 9: '20.492340087890625 --> 20.799999237060547', 10: '22.783540725708008 --> 22.920000076293945'}", 'mae': 1.3533774614334106, 'mse': 3.3998451232910156, 'rmse': 1.843866894136075, 'r2': -2.9446582794189453, 'reg_accuracy': 0.8489847715736041}'}
{'index': 'fl-winniio', 'status': 'success', 'message': 'Inference completed successfully', 'model_accuracy': '{'results': "{1: '20.580463409423828 --> 21.920000076293945', 2: '21.770084381103516 --> 21.04400062561035', 3: '28.23706817626953 --> 21.920000076293945', 4: '21.549779891967773 --> 22.149999618530273', 5: '22.088611602783203 --> 22.780000686645508', 6: '20.770658493041992 --> 20.010000228881836', 7: '21.775880813598633 --> 23.299999237060547', 8: '20.567359924316406 --> 21.399999618530273', 9: '24.005577087402344 --> 20.719999313354492', 10: '21.080963134765625 --> 23.1299991607666'}", 'mae': 1.0234222412109375, 'mse': 2.2549901008605957, 'rmse': 1.5016624457116172, 'r2': -1.4259724617004395, 'reg_accuracy': 0.9016497461928934}'}
{'index': 'fl-winniio', 'status': 'success', 'message': 'Inference completed successfully', 'model_accuracy': '{'results': "{1: '25.174299240112305 --> 20.729999542236328', 2: '22.640405654907227 --> 21.489999771118164', 3: '20.509401321411133 --> 20.010000228881836', 4: '20.58555793762207 --> 20.506000518798828', 5: '20.619409561157227 --> 19.452499389648438', 6: '20.38667869567871 --> 19.376667022705078', 7: '19.499414443969727 --> 21.038000106811523', 8: '20.547456741333008 --> 20.356666564941406', 9: '18.615236282348633 --> 21.143333435058594', 10: '19.832834243774414 --> 20.643333435058594'}", 'mae': 1.1806739568710327, 'mse': 2.9688289165496826, 'rmse': 1.723028994692104, 'r2': -1.5627341270446777, 'reg_accuracy': 0.8299492385786802}'}
```

You can also do a direct inference on the aggregator which requires inputting test data and its test
labels (i.e. expected predictions). The label must correspond to the given input and will be used to
compare against the actual predictions of the model's testing output. The data type of the test data
can be anything as long as fits the data type of the dataset. Below is an example for MNIST:
```bash
curl -X POST http://localhost:8081/infer \
-H "Content-Type: application/json" \
-d '{
  "input": [0.0,432.75,0.0,45.443333333333335,17.415,0.04369456467418299],
  "index": "fl-winniio"
}'
```

An example output looks like this:
```bash
{"prediction":"[19.737156]"}%
```

This will output a temperature prediction. 