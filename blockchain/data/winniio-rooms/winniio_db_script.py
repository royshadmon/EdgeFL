"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""


"""
Script to create PostgreSQL database and load MNIST data organized by node and round
"""
import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
# from torchvision import datasets
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
# from dotenv import load_dotenv
import time

# load_dotenv()

conn = psycopg2.connect(
    database=os.getenv("PSQL_DB_NAME"),
    user=os.getenv("PSQL_DB_USER"),
    password=os.getenv("PSQL_DB_PASSWORD"),
    host=os.getenv("PSQL_HOST"),
    port=os.getenv("PSQL_PORT"),
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

db_name = os.getenv("PSQL_DB_NAME")

def create_database():
    """Create PostgreSQL database if it doesn't exist."""

    # conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    # cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (f'{db_name}',))

    exists = cur.fetchone()
    if not exists:
        cur.execute(f'CREATE DATABASE {db_name}')
        print(f"Database '{db_name}' created")
    else:
        print(f"Database '{db_name}' already exists")

    # cur.close()
    # conn.close()


def create_node_table(conn, node_name):
    """Create a single table for a node that will contain all rounds of data."""
    # cur = conn.cursor()

    table_name = f"node_{node_name}"

    # DROP TABLE FIRST
    cur.execute(f'DROP TABLE IF EXISTS {table_name}')

    # CREATE TABLE
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            round_number INTEGER NOT NULL,
            data_type VARCHAR(10) NOT NULL,  -- 'train' or 'test'
            actuatorState DOUBLE PRECISION NOT NULL,
            co2Value DOUBLE PRECISION NOT NULL,
            eventCount DOUBLE PRECISION NOT NULL,
            humidity DOUBLE PRECISION NOT NULL,
            switchStatus DOUBLE PRECISION NOT NULL,
            temperature DOUBLE PRECISION NOT NULL,
            day DOUBLE PRECISION NOT NULL,
            time DOUBLE PRECISION NOT NULL,
            month DOUBLE PRECISION NOT NULL,
            date DOUBLE PRECISION NOT NULL,            
            label DOUBLE PRECISION NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on round_number for faster queries
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_round 
        ON {table_name}(round_number)
    """)

    conn.commit()
    # cur.close()
    return table_name


def insert_round_data(conn, table_name, round_num, df, data_type):
    """Insert data for a specific round into node's table."""
    # cur = conn.cursor()

    try:
        # Process in batches
        BATCH_SIZE = 10
        for i in range(0, len(df), BATCH_SIZE):
            batch_train = df[i:i + BATCH_SIZE]
            # batch_labels = labels[i:i + BATCH_SIZE]

            # Create batch of values for insertion
            args = []
            for data in batch_train.itertuples(index=False, name=None):
                args.append((round_num, data_type,) + data)

            # Batch insertion
            cur.executemany(
                f"""
                INSERT INTO {table_name} 
                (round_number, data_type, actuatorState, co2Value, eventCount, humidity, switchStatus, temperature, day, time, month, date, label)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                args
            )

            conn.commit()

        print(f"Inserted {len(df)} {data_type} samples for round {round_num} into {table_name}")

    except Exception as e:
        print(f"Error inserting data: {str(e)}")
        conn.rollback()
        raise
    # finally:
    #     cur.close()


def verify_round_data(conn, table_name, round_num):
    """Verify data counts for a specific round."""
    cur = conn.cursor()

    try:
        # Count training samples
        cur.execute(f"""
            SELECT COUNT(*) FROM {table_name} 
            WHERE round_number = %s AND data_type = 'train'
        """, (round_num,))
        train_count = cur.fetchone()[0]

        # Count test samples
        cur.execute(f"""
            SELECT COUNT(*) FROM {table_name} 
            WHERE round_number = %s AND data_type = 'test'
        """, (round_num,))
        test_count = cur.fetchone()[0]

        return train_count, test_count
    except Exception as e:
        print("Excection in verify_round_data")
    # finally:
    #     cur.close()


def main():
    # Configuration
    # NUM_NODES = 2
    NUM_ROUNDS = 5
    SAMPLES_PER_ROUND = 50
    TRAIN_SAMPLES_PER_ROUND = 0.8
    TEST_SAMPLES_PER_ROUND = 0.2

    print("Creating database...")
    create_database()

    # print("Downloading MNIST dataset...")
    # train_dataset = datasets.MNIST('..', train=True, download=True)
    # test_dataset = datasets.MNIST('..', train=False, download=True)
    # Process data from csv
    room_numbers = [12004, 12055, 12090]
    dataframes = []
    for rn in room_numbers:
        dataset = pd.read_csv(f'/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/data/winniio-rooms/room_{rn}.csv')
        dataset['label'] = dataset['temperature'].shift(-2)
        dataset.dropna(inplace=True)
        dataframes.append(dataset)



    # conn = get_db_connection()
    print("Connected to database")

    train_idx = 0
    test_idx = 0
    NUM_NODES = len(dataframes)

    try:
        # Process each node
        for node in range(1, NUM_NODES + 1):
            node_name = f"node{node}"
            print(f"\nProcessing room {room_numbers[node-1]} for {node_name}")

            # Create table for this node
            table_name = create_node_table(conn, node_name)

            # Process each round

            df_train, df_test = train_test_split(dataframes[node - 1], test_size=TEST_SAMPLES_PER_ROUND,
                                                 train_size=TRAIN_SAMPLES_PER_ROUND)

            df_train = np.array_split(df_train, NUM_ROUNDS)
            df_test = np.array_split(df_test, NUM_ROUNDS)

            for round_num in range(1, NUM_ROUNDS + 1):
                print(f"\nRound {round_num}")



                # train = df_train.drop(columns=['label'])
                # labels = df_train['label']

                # Insert training data for this round
                # train_end = train_idx + TRAIN_SAMPLES_PER_ROUND
                # train_images = train_dataset.data[train_idx:train_end]
                # train_labels = train_dataset.targets[train_idx:train_end]
                insert_round_data(conn, table_name, round_num, df_train[round_num-1], 'train')
                # train_idx = train_end

                # Insert test data for this round
                # test_end = test_idx + TEST_SAMPLES_PER_ROUND
                # test_images = test_dataset.data[test_idx:test_end]
                # test_labels = test_dataset.targets[test_idx:test_end]
                # test = df_test[node - 1].drop(columns=['label'])
                # labels = df_test['label']
                insert_round_data(conn, table_name, round_num, df_test[round_num-1], 'test')
                # test_idx = test_end

                # Verify data for this round
                train_count, test_count = verify_round_data(conn, table_name, round_num)
                print(f"Verification for {node_name} Round {round_num}:")
                print(f"Training samples: {train_count}")
                print(f"Test samples: {test_count}")


    finally:
        conn.close()
        print("\nData loading complete!")


if __name__ == "__main__":
    main()