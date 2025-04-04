import argparse
import csv
import os.path
import ast
import requests
import json

def csv2dict(data_file:str)->list:
    """
    Convert data in data_file into dictionary
    :args:
        data_file:str - file to read content from
    :params:
        csv_data:list - list of data in dictionary format from csv file
    :return
        csv_data:list
    """
    csv_data = []
    try:
        with open(data_file) as csvfile:
            for row in csv.DictReader(csvfile):
                csv_data.append(row)
    except Exception as e:
        raise Exception(f"Failed to extrapolate data from {data_file} (Error: {e})")

    return csv_data


def cleanup_data(csv_data:list)->list:
    """
    Given csv data, clean it up by converting to correct data types and add logical database and table names
    :args:
        csv_data:list - list of data in dictionary format from csv file
        db_name:str - name of database
        table_name:str - name of table
        process_type:str - type of process to use for cleanup
    :return:
        updated csv_data:list
    """
    for i in range(len(csv_data)):
        for column in csv_data[i].keys():
            try:
                csv_data[i][column] = ast.literal_eval(csv_data[i][column])
            except ast.ExceptHandler:
                # if fails ignore and keep as is
                pass

    return csv_data


def put_data(conn:str, csv_data:list, db_name:str, table_name:str):
    """
    Publish data via PUT
    :args:
        conn:str - REST connection string
        csv_data:list - list of data in dictionary format from csv file
        db_name:str - name of database
        table_name:str - name of table
    :params:
        headers:dict - REST headers
        payload:str - PUT payload
        response:requests.Response - REST response
    """
    headers = {
        'type': 'json',
        'dbms': db_name,
        'table': table_name,
        'mode': 'streaming',
        'Content-Type': 'text/plain'
    }

    payload = json.dumps(csv_data)

    try:
        response = requests.put(f"http://{conn}", headers=headers, data=payload)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed to put data to {conn} (Error: {e})")


def main():
    """
    The following provides an example for publishing data into AnyLog/EdgeLake via REST PUT - used for Winni.io demo
    Since the file name is room_12055.csv, I'm removing the .csv and keeping room_12055 as the table name
    :positional arguments:
        conn                  REST connection information
        data_file             comma seperated data files with path
    options:
        -h, --help            show this help message and exit
        --db-name DB_NAME     logical database name
    :params:
        data_files:list - comma seperated data files with path
        file_path:str - path to data file
        csv_data:list - list of data in dictionary format from csv file
    :sample-call:
        python3.10 edgefl/data/publish_data.py 104.237.130.228:32149 edgefl/data/winniio-rooms/room_12055.csv --db-name new_company
    """
    parse = argparse.ArgumentParser()
    parse.add_argument('conn', type=str, default=None, help='REST connection information')
    parse.add_argument('data_file', type=str, default=None, help='comma seperated data files with path')
    parse.add_argument('--db-name', type=str, default='my_db', help='logical database name')
    args = parse.parse_args()

    data_files = args.data_file.split(',') # separate list of files
    for data_file in data_files:
        file_path = os.path.expanduser(os.path.expandvars(data_file))
        if not os.path.exists(file_path):
            raise FIOError(f"File {file_path} does not exist")
        csv_data  = csv2dict(data_file=file_path) # read csv file

        if csv_data:
            # update data in dict(s) to have proper data type (ex. '1.3' --> 1.3)
            csv_data = cleanup_data(csv_data=csv_data)

            # publish data
            put_data(conn=args.conn, csv_data=csv_data, db_name=args.db_name, table_name=os.path.basename(data_file).split('.')[0])


if __name__ == '__main__':
    main()