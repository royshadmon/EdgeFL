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
from torchvision import datasets
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
# from dotenv import load_dotenv
import time

# load_dotenv()

# conn = psycopg2.connect(
#         database=os.getenv("PSQL_DB_NAME"),
#         user=os.getenv("PSQL_DB_USER"),
#         password=os.getenv("PSQL_DB_PASSWORD"),
#         host=os.getenv("PSQL_HOST"),
#         port=os.getenv("PSQL_PORT"),
#     )
# conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
# cur = conn.cursor()


def create_database():
    """Create PostgreSQL database if it doesn't exist."""

    # conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    # cur = conn.cursor()
    
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", ('mnist_fl',))

    exists = cur.fetchone()
    if not exists:
        cur.execute('CREATE DATABASE mnist_fl')
        print("Database 'mnist_fl' created")
    else:
        print("Database 'mnist_fl' already exists")
    
    # cur.close()
    # conn.close()

# def get_db_connection():
#     """Get connection to MNIST database."""
#     return psycopg2.connect(
#         dbname="postgres",
#         user="postgres",
#         password="",
#         host="localhost",
#         port="5432"
#     )

def create_node_table(conn, node_name):
    """Create a single table for a node that will contain all rounds of data."""
    # cur = conn.cursor()
    
    table_name = f"node_{node_name}"
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            round_number INTEGER NOT NULL,
            data_type VARCHAR(10) NOT NULL,  -- 'train' or 'test'
            image FLOAT[] NOT NULL,
            label INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index on round_number for faster queries
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_round 
        ON {table_name}(round_number)
    """)
    
    # conn.commit()
    # cur.close()
    return table_name

def insert_round_data(conn, table_name, round_num, images, labels, data_type):
    """Insert data for a specific round into node's table."""
    # cur = conn.cursor()
    
    try:
        # Process in batches
        BATCH_SIZE = 10
        for i in range(0, len(images), BATCH_SIZE):
            batch_images = images[i:i + BATCH_SIZE]
            batch_labels = labels[i:i + BATCH_SIZE]
            
            # Create batch of values for insertion
            args = []
            for img, lbl in zip(batch_images, batch_labels):
                img_array = img.numpy().flatten().tolist()
                args.append((round_num, data_type, img_array, int(lbl)))
            
            # Batch insertion
            cur.executemany(
                f"""
                INSERT INTO {table_name} 
                (round_number, data_type, image, label)
                VALUES (%s, %s, %s, %s)
                """,
                args
            )
            
            conn.commit()
        
        print(f"Inserted {len(images)} {data_type} samples for round {round_num} into {table_name}")
    
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
    NUM_ROUNDS = 25
    TRAIN_SAMPLES_PER_ROUND = 600
    TEST_SAMPLES_PER_ROUND = 100

    print("Creating database...")
    # create_database()
    
    print("Downloading MNIST dataset...")
    train_dataset = datasets.MNIST('..', train=True, download=True)
    test_dataset = datasets.MNIST('..', train=False, download=True)
    
    # conn = get_db_connection()
    print("Connected to database")
    
    train_idx = 0
    test_idx = 0
    
    try:
        # Process each node
        for node in range(1, NUM_NODES + 1):
            node_name = f"node{node}"
            print(f"\nProcessing {node_name}")
            
            # Create table for this node
            # table_name = create_node_table(conn, node_name)
            
            # Process each round
            for round_num in range(1, NUM_ROUNDS + 1):
                print(f"\nRound {round_num}")
                
                # Insert training data for this round
                train_end = train_idx + TRAIN_SAMPLES_PER_ROUND
                train_images = train_dataset.data[train_idx:train_end]
                train_labels = train_dataset.targets[train_idx:train_end]
                insert_round_data(conn, table_name, round_num, train_images, train_labels, 'train')
                train_idx = train_end
                
                # Insert test data for this round
                test_end = test_idx + TEST_SAMPLES_PER_ROUND
                test_images = test_dataset.data[test_idx:test_end]
                test_labels = test_dataset.targets[test_idx:test_end]
                insert_round_data(conn, table_name, round_num, test_images, test_labels, 'test')
                test_idx = test_end
                
                # Verify data for this round
                train_count, test_count = verify_round_data(conn, table_name, round_num)
                print(f"Verification for {node_name} Round {round_num}:")
                print(f"Training samples: {train_count}")
                print(f"Test samples: {test_count}")

                # Query example to view number of images
                # select round_number, data_type, COUNT(*) from node_node2 group by round_number,data_type order by round_number

    
    finally:
        conn.close()
        print("\nData loading complete!")

if __name__ == "__main__":
    main()