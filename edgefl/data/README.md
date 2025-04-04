# Publishing data

An application can publish data into AnyLog/EdgeLake using an array of southbound connectors, including: 
- MQTT
- REST: _put_ or _post_
- Kafka
- gRPC
- etc. 

## Backend Process
When a user sends data into AnyLog/EdgeLake (Operator node type) the following process occurs: 
1. Data is mapped to have correct key/value pairs 
When data is sent into AnyLog/EdgeLake, **not** using REST _PUT_, a mapping policy creates an association between the   
JSON data coming and user-defined preferred naming logic. This is done based on a mapping policy. 
When data is sent via a REST _PUT_, then, the information is stored as-is. 
   
2. If DNE - Blockchain policies defining the location of the data (cluster) and table definition are created. 
The table definition is based on the JSON object(s) being analyzed from the user input.
```json
{"cluster" : {"company" : "test",
               "name" : "test-cluster1",
               "status" : "active",
               "id" : "9b7d228178e18fe8512babb228a26912",
               "date" : "2025-03-30T04:41:38.202741Z",
               "ledger" : "global"}},

{"cluster" : {"parent" : "9b7d228178e18fe8512babb228a26912",
               "name" : "test-cluster1",
               "company" : "test",
               "table" : [{"dbms" : "test",
                           "name" : "rand_data",
                           "status" : "active"}],
               "source" : "Node at 170.187.157.30:32148",
               "id" : "1899ef4f168431d454db947a804c7b98",
               "date" : "2025-04-03T17:28:48.215004Z",
               "status" : "active",
               "ledger" : "global"}},

{"table" : {"name" : "rand_data",
             "dbms" : "test",
             "create" : "CREATE TABLE IF NOT EXISTS rand_data(  row_id SERIAL PRIMARY KEY"
                        ",  insert_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  tsd_name "
                        "CHAR(3),  tsd_id INT,  timestamp timestamp not null default now("
                        "),  value float ); CREATE INDEX rand_data_timestamp_index ON ran"
                        "d_data(timestamp); CREATE INDEX rand_data_tsd_index ON rand_data"
                        "(tsd_name, tsd_id); CREATE INDEX rand_data_insert_timestamp_inde"
                        "x ON rand_data(insert_timestamp);",
             "source" : "Processing JSON file",
             "id" : "1ef91f4b46560e289a9e6be869ccfe7c",
             "date" : "2025-04-03T16:31:24.861749Z",
             "ledger" : "global"}}
```
3. If DNE - create  a table definition, based on the blockchain policy, on the appropriate operator(s).

4. Convert JSON to SQL insert statement

5. Store data in a (partitioned) table.

6. If blobs (ex. images and videos) are included as part of the data, then the stored SQL data will contain a reference 
to the location of the blob(s), and store them either in (local) file or in MongoDB.

7. A reference of the data (row_id, tsd_name, tsd_id) is stored in `almgm.tsd_info`, which then is used for: 
   * Validation of the data 
   * HA across operator nodes (AnyLog only)

## User-Defined Process

### REST PUT
A _PUT_ command is simply specifying the logical information as the REST HEADERS and pre-mapped data in the payload.
An example can be found in [winniio](winniio-rooms/publish_data.py). 

### non-PUT 
All other processes (_POST_, Kafka, MQTT, etc.) require an extra steps **before** publishing data - declaring th mapping

1. Create a mapping policy - the example uses mp4 blob data 
```anylog
<mapping_policy={
    "mapping": {
        "id": "my-policy",
        "dbms": "bring [dbName]",
        "table": "bring [deviceName]",
        "source": {
            "bring": "[deviceName]",
            "default": "car_data"
        },
        "readings": "readings",
        "schema": {
            "timestamp": {
                "type": "timestamp",
                "bring": "[timestamp]"
           },
            "start_ts": {
                "type": "timestamp",
                "bring": "[start_ts]"
            },
            "end_ts": {
                "type": "timestamp",
               "bring": "[end_ts]"
            },
            "file": {
                "blob": true,
                "bring": "[binaryValue]",
                "extension": "mp4",
                "apply": "base64decoding",
                "hash": "md5",
                "type": "varchar"
            },
            "file_type": {
                "bring": "[mediaType]",
                "type": "string"
            },
            "num_cars": {
                "bring": "[num_cars]",
                "type": "int"
            },
            "speed": {
                "bring": "[speed]",
                "type": "float"
            }
        }
    }
}>

if !blockchain_source == master then blockchain insert where policy=!mapping_policy and local=true and master=!ledger_conn
else blockchain insert where policy=!mapping_policy and local=true and blockchain=optimism
```

2. Create a message client (example with REST)
```anylog
<run msg client where broker=rest and user-agent=anylog and log=false and topic=(
        name=my-policy and
        policy=my-policy
)> 
```

When data is not complex (ie without blobs), users can utilize the command with parameters as part of the message client
```anylog
<run msg client where broker=rest and user-agent=anylog and log=false and topic=(
    name=my-topic and
    dbms=new_company and
    table=rand_data and
    column.timestamp.timestamp="bring [timeestamp]" and
    column.start_ts.timestamp="bring [start_ts]" and
    column.end_ts.timestamp="bring [end_ts]" and
    column.location=(type=string and value="bring [location]") and 
    column.num_cars=(type=int and value="bring [num_cars]") and 
    column.speed=(type=float and value="bring [speed]") 
)>
```

3. Once a message client is set, data can be sent into AnyLog/EdgeLake. An example for publishing via POST can be found 
in [mnist](mnist/store_data.py)

