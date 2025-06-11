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
import kaggle
from sklearn.model_selection import train_test_split
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
dir_path_prefix = os.getenv("GITHUB_DIR")

def create_database():
    """Create PostgreSQL database if it doesn't exist."""

    # conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    # cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (f'{db_name}',))

    exists = cur.fetchone()
    if not exists:
        cur.execute(f"CREATE DATABASE {db_name}")
        print(f"Database '{db_name}' created")
    else:
        print(f"Database '{db_name}' already exists")

    # conn.close()


def create_node_table(conn, node_name):
    """Create a single table for a node that will contain all rounds of data."""

    table_name = f"node_{node_name}"

    # Prevents duped entries in the tables
    cur.execute(f"DROP TABLE IF EXISTS {table_name}")

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            round_number INTEGER NOT NULL,
            data_type VARCHAR(10) NOT NULL,  -- 'train' or 'test'
            image CHAR(16) NOT NULL, -- path to image in local directory
            width INTEGER NOT NULL DEFAULT 1024,
            height INTEGER NOT NULL DEFAULT 1024,
            class VARCHAR(16) NOT NULL, -- the label
            x_min DOUBLE PRECISION NOT NULL,
            y_min DOUBLE PRECISION NOT NULL,
            x_max DOUBLE PRECISION NOT NULL,
            y_max DOUBLE PRECISION NOT NULL,
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
        BATCH_SIZE = 10
        for i in range(0, len(df), BATCH_SIZE):
            batch_train = df[i:i + BATCH_SIZE]

            args = []
            for data in batch_train.itertuples(index=False, name=None):
                args.append((round_num, data_type,) + data)

            cur.executemany(
                f"""
                INSERT INTO {table_name}
                (round_number, data_type, image, width, height, class, x_min, y_min, x_max, y_max)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    NUM_NODES = 3
    NUM_ROUNDS = 10
    TRAIN_SAMPLES_PER_ROUND = 0.8 # this and below is percentages of total dataset
    TEST_SAMPLES_PER_ROUND = 0.2

    print("Creating database...")
    create_database()
    print("Connected to database")

    if os.path.exists("./raw"):
        print("Dataset already download")
    else:
        print("Downloading Chest XRays (Bounding Box) dataset...")
        kaggle.api.dataset_download_files(
            "huthayfahodeb/nih-chest-x-rays-bbox-version",
            "./raw",
            unzip=True
        )
        print("Downloaded dataset")

    dataframes = []
    dataset = pd.read_csv(f"{dir_path_prefix}/edgefl/data/chest_xrays_bbox/raw/tensorflow.csv")

    num_batches = NUM_NODES
    batch_size = len(dataset) // num_batches
    for i in range(num_batches):
        start_idx = i * batch_size
        # Last partial dataframe/batch will include all remaining rows
        end_idx = (i + 1) * batch_size if i != NUM_NODES - 1 else len(dataset)
        batch = dataset.iloc[start_idx:end_idx]
        dataframes.append(batch)

    try:
        # Process each node
        for node in range(1, NUM_NODES + 1):
            node_name = f"node{node}"
            print(f"\nProcessing {node_name}")

            # Create table for this node
            table_name = create_node_table(conn, node_name)

            # Process each round
            df_train, df_test = train_test_split(dataframes[node - 1],
                                                 test_size=TEST_SAMPLES_PER_ROUND,
                                                 train_size=TRAIN_SAMPLES_PER_ROUND)

            df_train = np.array_split(df_train, NUM_ROUNDS)
            df_test = np.array_split(df_test, NUM_ROUNDS)

            for round_num in range(1, NUM_ROUNDS + 1):
                print(f"\nRound {round_num}")

                # Training and testing data
                insert_round_data(conn, table_name, round_num, df_train[round_num - 1], "train")
                insert_round_data(conn, table_name, round_num, df_test[round_num - 1], "test")

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