import argparse
import datetime

import ast

import os
import gzip

import numpy as np
import struct
import requests
import json


FILE_PATH = os.path.expanduser(os.path.expandvars('$HOME/Anylog-Edgelake-Federated-Learning-Platform/edgefl/data/mnist/raw/t10k-labels-idx1-ubyte.gz'))


class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def __validate_file(file_path:str):
    """
    Validate image and label file exists and converted to full path
    :args:
        file_path: path to image file
    :params:
        full_path: full path to image file
    :return:
        full_path: full path to image file
    """
    full_path = os.path.expanduser(os.path.expandvars(file_path))
    if not os.path.isfile(full_path):
        raise IOError('File does not exist: {}'.format(full_path))
    return full_path


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


def create_policy(conn:str, db_name:str, table_name:str):
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
    """
    new_policy = {
        "mapping": {
            "id": "mnist-mapping",
            "dbms": db_name,
            "table": table_name,
            "schema": {
                "timestamp": {
                    "type": "timestamp",
                    "default": "now()",
                    "bring": "[timestamp]"
                },
                "image_file": {
                    "type": "string",
                    "default": "",
                    "value": "[image_file_name]"
                },
                "image": {
                    "blob": True,
                    "bring": "[image_content]",
                    "extension": "ubyte",
                    "apply": "opencv",
                    "hash": "md5",
                    "type": "varchar"
                },
                "labels_file": {
                    "type": "string",
                    "default": "",
                    "value": "[labels_file_name]"
                },
                "label": {
                    "blob": True,
                    "bring": "[label_content]",
                    "extension": "ubyte",
                    "apply": "opencv",
                    "hash": "md5",
                    "type": "varchar"
                }
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



def read_images(file_path)->np.ndarray:
    """
    Given a file_path - generate numpy array for label(s)
    :args:
        file_path:str - file to read content from
    :prarams:
        images:numpy.ndarray - extract image from file
    :return:
        images
    """
    images = None
    try:
        with gzip.open(file_path, 'rb') as f:
            # Read the header: magic number, number of images, number of rows, number of columns
            header = f.read(16)
            magic, num_images, rows, cols = struct.unpack(">IIII", header)

            # Read image data as an array of 8-bit unsigned integers
            image_data = np.frombuffer(f.read(), dtype=np.uint8)

            # Reshape into (num_images, rows, cols)
            images = image_data.reshape(num_images, rows, cols)
    except IOError:
        raise IOError("Unable to read labels from file %s" % file_path)

    return images


def read_labels(file_path)->np.ndarray:
    """
    Given a file_path - generate numpy array for label(s)
    :args:
        file_path:str - file to read content from
    :prarams:
        labels:numpy.ndarray - extract labels from file
    :return:
        labels
    """
    labels = None
    try:
        with gzip.open(file_path, 'rb') as f:
            # Read the header: magic number, number of labels
            header = f.read(8)
            magic, num_labels = struct.unpack(">II", header)

            # Read the label data (each label is an integer)
            labels = np.frombuffer(f.read(), dtype=np.uint8)
    except IOError:
        raise IOError("Unable to read labels from file %s" % file_path)

    return labels


def create_payload(db_name:str, image_file_name:str, image_content:np.ndarray, labels_file_name:str,
                   labels_content:np.ndarray)->str:
    payload = {
        "dbms": db_name,
        "table": "mnist_data",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_file": image_file_name,
        "image_content": image_content,
        "labels_file_name": labels_file_name,
        "label_content": labels_content,
    }

    return json.dumps(payload, cls=NumpyEncoder)


def main():
    parse = argparse.ArgumentParser()
    parse.add_argument('conn', type=str, default=None, help='REST connection information')
    parse.add_argument('image_file', type=__validate_file, default=None, help='image gz file')
    parse.add_argument('label_file', type=__validate_file, default=None, help='label gz file')
    parse.add_argument('--db-name', type=str, default='my_db', help='logical database name')
    parse.add_argument('--topic-name', type=str, default="mnist-mapping", help="logical topic name for msg client")
    args = parse.parse_args()

    # create_policy(conn=args.conn, db_name=args.db_name, table_name="[table_name]")
    # msg_client(conn=args.conn, topic=args.topic_name)

    image_content = read_images(args.image_file)
    label_content = read_labels(args.label_file)

    content = create_payload(db_name=args.db_name, image_file_name=os.path.basename(args.image_file),
                             image_content=image_content, labels_file_name=os.path.basename(args.label_file),
                             labels_content=label_content)

    headers = {
        'command': 'data',
        'topic': args.topic_name,
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain'
    }

    __post_data(conn=args.conn, payload=content, headers=headers)



if __name__ == '__main__':
    main()

