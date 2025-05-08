# Store data into AnyLog

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

4. [Query Data](get_data.py) - The example utilizes EdgeLake REST command to get information about the relevant files 
and then access them directly from MongoDB. 