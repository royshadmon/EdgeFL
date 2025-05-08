#----------------------------------------------------------------------------------------------------------------------#
# @Roy - in Remote-CLI:djangoProject/views.py
#   - line 1311 shows how we pull data for storage
#   - line 290 shows how we pull data for streaming
#----------------------------------------------------------------------------------------------------------------------#
import os.path

import requests
from pymongo import MongoClient
import gridfs


# Multiple table(s)
LOCAL_DIR = os.path.join(os.path.expanduser(os.path.expandvars(__file__)).split("get_data")[0], 'blobs')
if not os.path.isdir(LOCAL_DIR):
    os.makedirs(LOCAL_DIR)

# "sql mnist_fl extend=(+node_name, @ip, @port, @dbms_name, @table_name) and include=(test_node1) format = json and stat=false and timezone=Europe/Dublin  select  timestamp, file, round_number, data_type, label  from train_node1 order by timestamp desc limit 1 --> selection (columns: ip using ip and port using port and dbms using dbms_name and table using table_name and file using file)"
QUERY = "sql mnist_fl extend=(+node_name, @ip, @port, @dbms_name, @table_name) and format = json and stat=false and timezone=Europe/Dublin  select  timestamp, file, round_number, data_type, label  from train_node1 order by timestamp desc --> selection (columns: ip using ip and port using port and dbms using dbms_name and table using table_name and file using file)"
URL = "10.0.0.131:32149"

MONGODB_IP = "10.0.0.131"
MONGODB_PORT = 27017  # Default MongoDB port
USERNAME = "admin"
PASSWORD = "passwd"

def get_data(query:str=QUERY):
    headers = {
        "command": query,
        "User-Agent": "AnyLog/1.23",
        "destination": "network"  # this is instead of `run client ()`
    }

    try:
        r = requests.get(url=f"http://{URL}", headers=headers)
    except Exception as error:
        raise Exception
    else:
        if not 200 <= int(r.status_code) < 300:
            raise ConnectionError(r.status_code)

    return r.json()['Query']

def mongo_get_data(db_name, local_dir, filename):
    with MongoClient(f"mongodb://{USERNAME}:{PASSWORD}@{MONGODB_IP}:{MONGODB_PORT}/") as conn:
        fs = gridfs.GridFS(conn[f'blobs_{db_name}'])
        file_cursor = fs.find_one({"filename": filename})
        if file_cursor:
            with open(os.path.join(local_dir, filename), 'wb') as f:
                f.write(file_cursor.read())

def main():
    data = get_data()
    for result in data:
        # {'node_name': 'ori-test-operatorX', 'ip': '172.19.0.2', 'port': '32148', 'dbms_name': 'mnist_fl', 'table_name': 'train_node1', 'timestamp': '2025-01-14 19:56:53.074069', 'file': '0d7234a2184494cc6809c07768d4ebce.png', 'round_number': 12, 'data_type': 'train', 'label': 7}
        filename = f"{result['table_name']}.{result['file']}"
        mongo_get_data(db_name=result['dbms_name'], local_dir=LOCAL_DIR, filename=filename)

if __name__ == '__main__':
    main()

