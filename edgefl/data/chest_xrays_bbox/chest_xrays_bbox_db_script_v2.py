"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""

import argparse
import datetime
import os
import json
import numpy as np
import pandas as pd
import kaggle
from sklearn.model_selection import train_test_split
import time
import requests

DIR_PATH_PREFIX = os.getenv("GITHUB_DIR", os.path.dirname(__file__))
DB_NAME = os.getenv("PSQL_DB_NAME", "mnist_fl")



def post_data(conn:str, headers:dict, payload=None):
    try:
        response = requests.post(url=f'http://{conn}', headers=headers, data=payload)
        response.raise_for_status()
    except Exception as error:
        raise Exception(f'Failed to execute POT against {conn} (Error: {error})')



def blobs_policy(conn:str, policy_id:str='xray-data'):
    """
    For POST commands, user needs to specify a mapping policy between the data and the ingestion process
    :args:
        conn:str - REST connection information
        policy_id:str - policy ID
    :params:
        headers:dict - REST heeader
        new_policy:dict - Mapping policy

    """
    # check if mapping exists
    headers = {
        "command": f"blockchain get mapping where id={policy_id}",
        "User-Agent": "AnyLog/1.23",
    }
    try:
        response = requests.get(url=f"http://{conn}", headers=headers)
        response.raise_for_status()
    except Exception as error:
        raise Exception(f'Failed to execute GET against {conn} (Error: {error})')
    else:
        if response.json():
            return

    # create mapping policy if DNE
    new_policy = {"mapping": {
        "id": policy_id,
        "dbms": "bring [dbms]",
        "table": "bring [table]",
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
            "data_type": {  # train or test
                "type": "string",
                "bring": "[data_type]"
            },
            "file": {
                "blob": True,
                "bring": "[image]",
                "extension": "jpeg",
                "apply": "opencv", # I'm guessing the data is in numpy format
                "hash": "md5",
                "type": "varchar"
            },
            "width": {
                "type": "float",
                "bring": "[width]"
            },
            "height": {
                "type": "float",
                "bring": "[height]"
            },
            "class": {
                "type": "string",
                "bring": "[class]"
            },
            "bbox": {
                "type": "string",
                "bring": "bbox"
            }
    }}}

    headers = {
        'command': 'blockchain insert where policy=!new_policy and local=true and master=!ledger_conn',
        'User-Agent': 'AnyLog/1.23',
    }
    post_data(conn=conn, headers=headers, payload=f"<new_policy={json.dumps(new_policy)}>")


def msg_client(conn:str, policy_id:str='xray-data'):
    headers = {
        'command': f'get msg client where topic={policy_id}',
        'User-Agent': 'AnyLog/1.23'
    }
    try:
        response = requests.get(url=f'http://{conn}', headers=headers)
        response.raise_for_status()
    except Exception as error:
        raise Exception(f'Failed to execute GET against {conn} (Error: {error})')
    else:
        if response.text.strip() != 'No message client subscriptions':
            return

    headers = {
        'command': f'run msg client where broker=rest and user-agent=anylog and log=false and topic=(name={policy_id} and policy={policy_id})',
        'User-Agent': 'AnyLog/1.23'
    }
    post_data(conn=conn, headers=headers, payload=None)




def generate_round_data(db_name:str, table_name:str, round_num:int, batch_size:int, df, data_type:str):
    """
    generate payload(s) for current round
    :args:
        round_num:int -  current round
        batch_size:innt - baatch size
        df - dataframe(s)
        data_type:str - train || test
    :params:
        payloads:list - list of payload
        pyloaad:dict - content to store in EdgeLake
    :return:
        payloads
    """
    payloads = []
    timestamp = datetime.datetime.now().strfrmt('%Y-%m-%dT%H:%M:%S.%fZ')
    for i in range(0, len(df), batch_size):
        batch_train = df[i:i + batch_size]

        args = []
        for data in batch_train.itertuples(index=False, name=None):
            args.append((round_num, data_type,) + data)

        image, width, height, cls, x_min, y_min, x_max, y_max = data
        payload = {
            'dbms': db_name,
            'table': table_name,
            'timestamp': timestamp,
            'round_number': round_num,
            'data_type': data_type,
            'image': image,
            'width': width,
            'height': height,
            'class': cls,
            'bbox': [x_min, y_min, x_max, y_max],
        }

        payloads.append(payload)

    return payloads


def main():
    parse = argparse.ArgumentParser()
    parse.add_argument('conn', type=str, default=None, help='REST connection information')
    parse.add_argument('--db-name', type=str, default=DB_NAME, help='logical database name')
    parse.add_argument('--table-name', type=str, default=None)
    parse.add_argument('--topic', type=str, default='xray-data', help='message client topic name')
    parse.add_argument('--num-rounds', type=int, default=10, help='')
    parse.add_argument('--train-sample-size', type=int, default=0.8, help='train samples per round')
    parse.add_argument('--test-sample-size', type=int, default=0.2, help='test samples per round')
    parse.add_argument('--batch-size', type=int, default=10, help='')
    args = parse.parse_args()

    conns = arags.conn.split(',')
    for conn in conns:
        blobs_policy(conn=conn, policy_id=args.topic)
        msg_client(conn=conn, policy_id=args.topic)

    headers = {
        'command': 'data',
        'topic': topic,
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain'
    }
    dataframes = []
    dataset = pd.read_csv(os.path.join(DIR_PATH_PREFIX, 'tensorflow.csv'))
    batch_size = len(dataset) // len(conns)
    for i in range(len(conns)):
        start_idx = i * batch_size
        end_idx = (i + 1) * batch_size if i != len(conns) - 1 else len(dataset)
        batch = dataset.iloc[start_idx:end_idx]
        dataframes.append(batch)

    for conn in conns:
        df_sets = {'test': None, 'train': None}

        df_train, df_test = train_test_split(dataframes[node - 1], test_size=args.test_samples_size,
                                             train_size=args.train_samples_size)
        df_sets['train'] = np.array_split(df_train, args.num_rounds)
        df_sets['test'] = np.array_split(df_test, args.num_rounds)

        for crt_round in range(1, args.num_rounds+1):
            for data_type in df_sets:
                table_name = f"{args.table_name.replace(' ', '_').replace('-', '_')}_{data_type}" if ags.table_name else dataset
                payload = generate_round_data(db_name=args.db_name, table_name=table_name, round_num=crt_round,
                                              batch_size=args.batch_size, df=df_sets[data_type][crt_round-1],
                                              data_type=data_type)
                post_data(conn=conn, headers=headers, payload=payload)



if __name__ == '__main__':
    msg_client(conn='10.0.0.147:32149')
    # main()









