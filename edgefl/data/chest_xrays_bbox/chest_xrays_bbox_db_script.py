"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""
import argparse
import json
import time

import requests

"""
Script to create PostgreSQL database and load MNIST data organized by node and round
"""
import os
import numpy as np
import pandas as pd
import kaggle
from sklearn.model_selection import train_test_split

# load_dotenv()

dir_path_prefix = os.getenv("GITHUB_DIR")


def __put_data(conn:str, payload:(list or str or dict), headers:dict):
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
        payload = json.loads(payload)
        for row in payload:
            response = requests.put(url=f"http://{conn}", data=json.dumps(row), headers=headers)
            response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed to execute POST against {conn} (Error: {e})")


def create_header(db_name:str, table_name:str):
    header = {
        "type": "json",
        "dbms": db_name,
        "table": table_name,
        "mode": "streaming",
        "Content-Type": "text/plain"
    }
    return header



def main():
    parse = argparse.ArgumentParser()
    parse.add_argument('conn', type=str, default=None, help='REST connection information')
    parse.add_argument('--db-name', type=str, default='mnist', help='logical database name')
    parse.add_argument('--num-rounds', type=int, default=5, help='Number of training rounds to add')
    parse.add_argument('--num-rows', type=int, default=50, help='')
    # parse.add_argument('--test-split', type=int, default=0.2, help='')

    # create tsd_info
    args = parse.parse_args()

    # for cmd_type in ['drop', 'create']:
    #     try:
    #         response = requests.post(f'http://{args.conn}',
    #                                  headers={'command': f"{cmd_type} table tsd_info where dbms=almgm",
    #                                           'User-Agent': 'AnyLog/1.23'})
    #         response.raise_for_status()
    #     except Exception as e:
    #         print("Failed to execute POST against {args.conn} (Error: {e})")
    #         # raise Exception(f"Failed to execute POST against {args.conn} (Error: {e})")


    time.sleep(2)

    # Configuration
    NUM_ROUNDS = args.num_rounds
    TRAIN_SAMPLES_PER_ROUND = 0.8 # this and below is percentages of total dataset
    TEST_SAMPLES_PER_ROUND = 0.2



    if os.path.exists("./raw"):
        print("Dataset already download")
    else:
        print("Downloading Chest XRays (Bounding Box) dataset...")
        # https://www.kaggle.com/datasets/huthayfahodeb/nih-chest-x-rays-bbox-version
        kaggle.api.dataset_download_files(
            "huthayfahodeb/nih-chest-x-rays-bbox-version",
            "./raw",
            unzip=True
        )
        print("Downloaded dataset")

    dataframes = []
    dataset = pd.read_csv(f"{dir_path_prefix}/edgefl/data/chest_xrays_bbox/raw/tensorflow.csv")

    dataset = dataset.rename(columns={"xmin": "x_min", "ymin": "y_min", "xmax": "x_max", "ymax": "y_max"})

    NUM_ROWS = args.num_rows



    try:
        # Process each node
        for round in range(1, NUM_ROUNDS + 1):
            random_rows = dataset.sample(NUM_ROWS)
            random_rows['round_number'] = round

            # Process each round
            df_train, df_test = train_test_split(random_rows,
                                                 test_size=TEST_SAMPLES_PER_ROUND,
                                                 train_size=TRAIN_SAMPLES_PER_ROUND)



            print(f"\nRound {round}")

            # create header
            train_header = create_header(db_name=args.db_name, table_name="xray_train")
            test_header = create_header(db_name=args.db_name, table_name="xray_test")

            # Insert train data
            print("Inserting to xray_train")
            try:
                __put_data(conn=args.conn, headers=train_header, payload=df_train.to_json(orient='records'))
            except Exception as error:
                raise Exception

            # Insert train data
            print("Inserting to xray_test")
            try:
                __put_data(conn=args.conn, headers=test_header, payload=df_test.to_json(orient='records'))
            except Exception as error:
                raise Exception
            #

    finally:
        print("\nData loading complete!")


if __name__ == "__main__":
    main()