from flask import Flask, jsonify, request
import os
import kaggle
import pandas as pd
from sqlalchemy import create_engine
import threading
import time
import requests
import numpy as np

from psycopg import sql
import psycopg

app = Flask(__name__)

# psql -U postgres
# ^ will prompt u to enter postgres (default superuser) password if you set one

# from here, we can technically create a remote postgresql server but i don't want to set that up rn tbh
# since data processing code is here anyways, just create your own db and user

# CREATE USER edge WITH PASSWORD 'lake';
# ALTER USER edge CREATEDB 
# ^ allow user to create databases

# don't do this line below, just here for reference
# CREATE DATABASE smoking OWNER edge

# from here, /q to close postgresql terminal
# can log in from now with psql -U edge -d smoking -W

# SQL_USER = "edge" 
# SQL_PASSWORD = "lake"
SQL_USER = "postgres" 
SQL_PASSWORD = "Noobodiii!!!123"
PORT = 5432 # default upon postgresql setup
DB_NAME = "smoking"
HOST = "localhost"

def get_server_connection():
    return psycopg.connect(
        dbname="postgres",  # Connect to the default database initially, need to do this before creating another database
        user=SQL_USER,
        password=SQL_PASSWORD,
        host=HOST,
        port=PORT
    )

def get_db_connection():
    return psycopg.connect(
        dbname=DB_NAME,
        user=SQL_USER,
        password=SQL_PASSWORD,
        host=HOST,
        port=PORT
    )

def create_new_db():
    with get_server_connection() as conn:
            conn.autocommit = True  # Enable autocommit to create a database
            with conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
                if cur.fetchone():  # Database already exists
                    print(f"Database '{DB_NAME}' already exists.")
                    cur.execute(f"DROP DATABASE {DB_NAME};")
                    print(f"Database '{DB_NAME}' dropped successfully.")
                
                # create new database
                cur.execute(f"CREATE DATABASE {DB_NAME};")
                print(f"Database '{DB_NAME}' created successfully.")

def initialize_tables(num_nodes=1):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Create tables dynamically based on num_nodes
            for i in range(num_nodes):
                table_name = f"node_{i}"
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id SERIAL PRIMARY KEY,
                        round INT NULL,
                        data TEXT NULL 
                    );
                """)
                print(f"Table '{table_name}' created successfully with empty 'round' and 'data' columns.")

        # Commit the transaction to save changes
        conn.commit()
        return {"status": "success", "message": f"{num_nodes} tables created in '{DB_NAME}'"}

    except Exception as e:
        return {"error": str(e)}

    finally:
        # Ensure the connection is closed
        conn.close()

@app.route('/initialize', methods=['POST'])
def initialize():
    data = request.get_json()
    num_nodes = data.get('num_nodes')

    # create new db
    create_new_db()
    print("database created")
    # initialize tables
    result = initialize_tables(num_nodes)
    print("tables created")

    if "error" in result:
        return jsonify(result), 500
    return jsonify(result), 201

# when a node recieves a batch of data, it should add it to it's corresponding table in the database
@app.route('/add_data', methods=['POST'])
def add_data():

    data = request.get_json()
    node_id = data.get('node_id')
    batch_data = data.get('batch_data')
    round = data.get('round')

    # Determine the table name for this node
    table_name = f"node_{node_id}"

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Insert each batch entry with the provided round number
            for entry in batch_data:
                cur.execute(
                    sql.SQL("INSERT INTO {table} (round, data) VALUES (%s, %s)")
                    .format(table=sql.Identifier(table_name)),
                    [round, entry]
                )
            print(f"Data added to table '{table_name}' for round {round}.")

            # print_database_status();

        conn.commit()
        return jsonify({"status": "success", "message": f"Data added to {table_name} for round {round}"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

# given a round number and a node, return the data associated
@app.route('/get_data', methods=['GET'])
def get_data():
    # Retrieve node_id and round from query parameters
    node_id = request.args.get('node_id', type=int)
    round_number = request.args.get('round', type=int)

    # Validate input
    if not node_id or round_number is None:
        return jsonify({"error": "Both 'node_id' and 'round' are required"}), 400

    # Determine the table name for this node
    table_name = f"node_{node_id}"

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Query to retrieve all data for the specified round
            cur.execute(
                sql.SQL("SELECT data FROM {table} WHERE round = %s")
                .format(table=sql.Identifier(table_name)),
                [round_number]
            )
            data = cur.fetchall()

            # Format data as a list of strings
            data_list = [row[0] for row in data]

        return jsonify({"node_id": node_id, "round": round_number, "data": data_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

def print_database_status():
    try:
        # Connect to the specific database
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get list of tables
            cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';")
            tables = cur.fetchall()

            print("\nTables in the database:")
            for table in tables:
                print(f"Table: {table[0]}")
                
                # Retrieve data from each table
                cur.execute(f"SELECT * FROM {table[0]};")
                rows = cur.fetchall()
                print(f"Contents of {table[0]}:")
                for row in rows:
                    print(row)

    except Exception as e:
        print("Error accessing database:", e)


if __name__ == '__main__':
    app.run(port=5000)

