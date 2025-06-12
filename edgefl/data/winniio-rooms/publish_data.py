import argparse
import os.path
import requests

import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from tensorflow.python.ops.gen_experimental_dataset_ops import dataset_from_graph

def put_data(conn:str, db_name:str, table:str, payload):
    headers = {
        'type': 'json',
        'dbms': db_name,
        'table': table,
        'mode': 'streaming',
        'Content-Type': 'text/plain'
    }
    try:
        for row in payload:
            response = requests.put(url=f'http://{conn}', headers=headers, data=json.dumps(row))
            response.raise_for_status()
    except Exception as error:
        raise Exception




# Configuration
def read_file(file_path:str):
    full_path = os.path.expanduser(os.path.expandvars(file_path))
    if not os.path.isfile(full_path):
        raise FileNotFoundError

    dataset = pd.read_csv(full_path)
    dataset['label'] = dataset['temperature'].shift(-2)
    dataset.dropna(inplace=True)

    return  dataset


def generate_data(dataset, train_split, test_split, num_rounds):
    json_output = {
        "train": [],
        "test": []
    }

    df_train, df_test = train_test_split(dataset, train_size=train_split, test_size=test_split)
    df_train_rounds = np.array_split(df_train, num_rounds)
    df_test_rounds = np.array_split(df_test, num_rounds)

    for round_counter in range(1, num_rounds+1):
        train_batch = df_train_rounds[round_counter - 1].copy()
        train_batch['round_number'] = round_counter
        train_batch['data_type'] = 'train'

        train_json = train_batch.to_dict(orient="records")
        json_output["train"].append(train_json)

        test_batch = df_test_rounds[round_counter - 1].copy()
        test_batch['round_number'] = round_counter
        test_batch['data_type'] = 'test'

        test_json = test_batch.to_dict(orient="records")
        json_output["test"].append(test_json)

    return json_output


def  main():
    parse = argparse.ArgumentParser()
    parse.add_argument('conn', type=str, default=None, help='REST connection information')
    parse.add_argument('file_path', type=str, default=None, help='CSV file to pull data from')
    parse.add_argument('--db-name', type=str, default='mnist', help='logical database name')
    parse.add_argument('--num-rounds', type=int, default=5, help='')
    parse.add_argument('--train-split', type=int, default=0.8, help='')
    parse.add_argument('--test-split', type=int, default=0.2, help='')
    args = parse.parse_args()

    dataset = read_file(file_path=args.file_path)
    json_output = generate_data(dataset=dataset, train_split=args.train_split, test_split=args.test_split, num_rounds=args.num_rounds)

    table_name = args.file_path.rsplit('\\')[-1].rsplit('/', 1)[-1].split('.csv')[0]
    for batch_type in json_output:
        put_data(conn=args.conn, db_name=args.db_name, table=f'{table_name}_{batch_type}', payload=json_output[batch_type])


if __name__ == '__main__':
    main()