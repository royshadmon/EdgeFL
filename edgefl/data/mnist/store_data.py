import argparse
import datetime
import ast
import os
import gzip

from pydantic_core.core_schema import dataclass_args_schema
from torchvision import datasets
from email.mime.image import MIMEImage
from ipaddress import ip_address
from sqlite3.dbapi2 import paramstyle

import numpy as np
import struct
import requests
import json

TABLE_NAME = 'mnist_data'
DATA_HEADER = {
    'command': 'data',
    'topic': None,
    'User-Agent': 'AnyLog/1.23',
    'Content-Type': 'text/plain'
}



def __post_data(conn:str, payload:(list or str or dict), headers:dict):
    """
    Execute POST command
    :args:
        conn: name of database connection
        payload: list of tuples containing image data
        headers: dictionary of headers
    :params:
        response:requests response object
    """
    try:
        response = requests.post(url=f"http://{conn}", data=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed to execute POST against {conn} (Error: {e})")


def msg_client(conn:str, topic:str):
    """
    Execute `run msg client` to accept data via POST
    :args:
        conn:str - REST connection string
        topic:str - topic name
    :params:
        headers:dict - REST connection headers
    """
    headers = {
        "command": f"run msg client where broker=rest and user-agent=anylog and log=false and topic=(name={topic} and policy=mnist-mapping)",
        "User-Agent": "AnyLog/1.23"
    }

    __post_data(conn=conn, payload=None, headers=headers)


def create_policy(conn:str):
    """
    Create mapping policy if DNE
    :args:
        conn:str - REST connection information
        db_name:str - logical database name
        table_name:str - logical table name
    :params:
        new_policy:dict - mapping policy
        response:requests.Response - HTTP response
        headers:dict - HTTP headers
    :table:
    CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            round_number INTEGER NOT NULL,
            data_type VARCHAR(10) NOT NULL,  -- 'train' or 'test'
            image FLOAT[] NOT NULL,
            label INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    new_policy = {
        "mapping": {
            "id": "mnist-mapping",
            "dbms": 'bring [dbms]',
            "table": 'bring [table]',
            "schema": {
                "timestamp": {
                    "type": "timestamp",
                    "default": "now()",
                    "bring": "[timestamp]"
                },
                "round_number": {
                    "type": "int",
                    "bring": "[round_number]"
                },
                "data_type": { # train or test
                    "type": "string",
                    "bring": "[data_type]"
                },
                "image": {
                    "type": "int",
                    "bring": "[image]"
                },
                "label": {
                    "type": "int",
                    "bring": "[label]"
                },
                # "live_image": { # this is what we're able to
                #     "blob": True,
                #     "bring": "[live_image]",
                #     "extension": "png",
                #     "apply": "opencv",
                #     "hash": "md5",
                #     "type": "varchar"
                # }
            }
        }
    }

    try:
        response = requests.get(url=f"http://{conn}",
                                headers={"command": "blockchain get mapping where id=mnist-mapping bring.count",
                                         "User-Agent": "AnyLog/1.23"})
        response.raise_for_status()

    except Exception as e:
        raise Exception(f"Failed to execute GET against {conn} (Error: {e})")
    else:
        response = ast.literal_eval(response.text)

    if len(response) == 0:
        headers = {
            "command": "blockchain insert where policy=!new_policy and local=true and master=!ledger_conn",
            "User-Agent": "AnyLog/1.23",
        }
        payload = f"<new_policy={json.dumps(new_policy)}>"
        __post_data(conn=conn, payload=payload, headers=headers)


class MnistData:
    def __init__(self):
        self.train_dataset = datasets.MNIST('..', train=True, download=True)
        self.test_dataset = datasets.MNIST('..', train=False, download=True)

    def __create_payload(self, db_name:str, table_name:str, round_number:int, data_type:str, image, label:int)->dict:
        return {
            'dbms': db_name,
            'table': table_name,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'round_number': round_number,
            'data_type': data_type,
            'image': image.tolist(),
            'label': label.tolist(),
            # "live_image": (image.unsqueeze(1).float() / 255.0).tolist()
        }

    def generate_data(self, conn_id:int, db_name:str, current_round:int, data_type:str, data_size:int, idx:int=0)->(dict, int) or None:
        idx_end = idx + data_size
        image = self.train_dataset.data[idx:idx_end] if data_type == 'training' else self.test_dataset.data[idx:idx_end]
        label = self.train_dataset.targets[idx:idx_end] if data_type == 'training' else self.test_dataset.targets[idx:idx_end]

        # Ensure slicing is valid
        if image.nelement() == 0:
            return None

        payload = self.__create_payload(db_name=db_name, table_name=f'{TABLE_NAME}{conn_id}_{data_type}',
                                        round_number=current_round, data_type=data_type, image=image, label=label)

        return payload, idx_end


def main():
    """
    Steps:
        1. against Master declare policy
            python3 store_data.py 10.0.0.81:32049 --db-name mnist --declare-policy
        2. publish data
    :return:
    """
    parse = argparse.ArgumentParser()
    parse.add_argument('conn', type=str, default=None, help='REST connection information')
    parse.add_argument('--db-name', type=str, default='mnist', help='logical database name')
    parse.add_argument('--num-rounds', type=int, default=25, help='')
    parse.add_argument('--train-sample-size', type=int, default=600, help='')
    parse.add_argument('--test-sample-size', type=int, default=100, help='')

    parse.add_argument('--declare-policy', type=bool, nargs='?', const=True, default=False, help='declare data mapping policy')
    parse.add_argument('--declare-mqtt', type=bool, nargs='?', const=True, default=False, help='enable MQTT client')
    parse.add_argument('--publish-data',  type=bool, nargs='?', const=True, default=False, help='Publish data to operator node(s)')
    # parse.add_argument('image_file', type=__validate_file, default=None, help='image gz file')
    # parse.add_argument('label_file', type=__validate_file, default=None, help='label gz file')
    parse.add_argument('--topic-name', type=str, default="mnist-mapping", help="logical topic name for msg client")
    args = parse.parse_args()

    conns = args.conn.split(',')
    train_idx = 0
    test_idx = 0
    mnist = MnistData()
    DATA_HEADER['topic'] = args.topic_name


    for conn in conns:
        if args.declare_policy is True: # declare mapping policy
            create_policy(conn=conn)
        if args.declare_mqtt is True: # run mqtt client
            msg_client(conn=conn, topic=args.topic_name)

        if args.publish_data is True:
            for round_num in range(0, args.num_rounds):
                train_payload, train_idx = mnist.generate_data(db_name=args.db_name, conn_id=conns.index(conn) + 1, current_round=round_num,
                                                               data_type='train', data_size=args.train_sample_size,
                                                               idx=train_idx)
                test_payload, test_idx = mnist.generate_data(db_name=args.db_name, conn_id=conns.index(conn) + 1, current_round=round_num,
                                                               data_type='test', data_size=args.test_sample_size,
                                                               idx=test_idx)

                data = []
                if train_payload is not None:
                    data.append(train_payload)
                if test_payload is not None:
                    data.append(test_payload)
                if data:
                    __post_data(conn=conn, payload=json.dumps(data), headers=DATA_HEADER)



if __name__ == '__main__':
    main()

