Store data into AnyLog

**Steps**
1. Connect to database - this can be done by updating the configurations when running deploymnent-scripts or 
running the commands in [database_connection.al](database_connection.al)

I used docker containers, and updated the [operator configurations](https://github.com/AnyLog-co/docker-compose/tree/os-dev/docker-makefile/operator-configs)
as follows: 
* In _basic configs_ 
  * Enable NoSQL 
  * Default database to `mnist_fl`
  * store data in NoSQL database 
  * reuse images
* In advance configs 
  * Enable using Remote CLI -- this is for querying the data

2. Declare mapping policy on the blockchain - [anylog_policy.al](anylog_policy.al)

3. Insert data using  [publish_data.py](publish_data.py)

Query; 
```anylog 
sql mnist_fl info = (dest_type = rest) and extend=(+node_name, @ip, @port, @dbms_name, @table_name) and format = json and timezone=Europe/Dublin  select  timestamp, file, round_number, data_type, label  from train_node1  order by timestamp desc --> selection (columns: ip using ip and port using port and dbms using dbms_name and table using table_name and file using file)
```