"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""


from asyncio import sleep

import requests
import socket
import json

from requests import RequestException


def insert_policy(el_url, policy):
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': 'blockchain insert where policy = !my_policy and local = true and blockchain = master'
    }

    response = requests.post(el_url, headers=headers, data=policy)
    return response

# TODO: fix proper blockchain update command
# def update_policy(el_url, policy_id, policy):
#     headers = {
#         'User-Agent': 'AnyLog/1.23',
#         'Content-Type': 'text/plain',
#         'command': f'blockchain update to master {policy_id} !my_policy'
#     }
#     response = requests.post(el_url, headers=headers, data=policy)
#     return response

def delete_policy(el_url, policy_id):
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': f'blockchain delete policy where id = {policy_id} and local = true and blockchain = master'
    }

    response = requests.post(el_url, headers=headers, data=None)
    return response

def check_policy_inserted(el_url, policy):

    response = insert_policy(el_url, policy)
    if response.status_code == 200:
        print(f'Successfully inserted policy {policy}')
        return response
    else:
        headers = {
            'User-Agent': 'AnyLog/1.23',
            'Content-Type': 'text/plain',
            'command': 'blockchain prepare policy !my_policy'
        }

        response = requests.post(el_url, headers=headers, data=policy)

        headers = {
            'User-Agent': 'AnyLog/1.23',
            'Content-Type': 'text/plain',
            'command': 'get !my_policy'
        }
        # print(f"check_policy_inserted: {response.status_code}")
        # print(response.status_code)

        response = requests.get(el_url, headers=headers)
        retrieved_policy = json.loads(response.content.decode('utf-8'))

        if retrieved_policy:
            return True

        return False

def get_policies(el_url, policy_type='*', condition=None):
    command = f'blockchain get {policy_type} {condition if condition else ""}'
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': command
    }
    response = requests.get(el_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Request failed with status code {response.status_code}: {response.reason}. Command: {command}")

    data = response.json() # [{policy_name: {..., 'id': ..., ...}}]
    policies = []
    for policy in data:
        policies.append(policy[policy_type])
    return policies # [{'attr1': ..., 'attr2': ..., ...}, {'attr1': ..., 'attr2': ..., ...}, ...]

def get_policies(el_url, index='*', condition=None):
    command = f'blockchain get {index} {condition if condition else ""}'
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': command
    }
    response = requests.get(el_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Request failed with status code {response.status_code}: {response.reason}. Command: {command}")

    data = response.json() # [{policy_name: {..., 'id': ..., ...}}]
    policies = []
    for policy in data:
        policies.append(policy[index])
    return policies # [{'attr1': ..., 'attr2': ..., ...}, {'attr1': ..., 'attr2': ..., ...}, ...]


def get_policy_id_by_name(el_url, policy_name):
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': f'blockchain get {policy_name}'
    }
    response = requests.get(el_url, headers=headers)
    data = response.json()
    if not data:
        return None
    policy_id = data[0][policy_name]['id'] # [{policy_name: {..., 'id': ..., ...}}]
    return policy_id

def get_all_databases(edgelake_node_url):
    """
    Gets all databases that the specified EdgeLake node is connected to.

    :param edgelake_node_url: The URL of the EdgeLake node to fetch the databases list.
    :return: Set of all the connected databases.
    :rtype: set()
    """
    command = "get databases"
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'command': command,
    }

    try:
        # Send the POST request
        response = requests.get(edgelake_node_url, headers=headers)

        # Raise an HTTPError if the response code indicates failure
        response.raise_for_status()

        # Parsing response content
        response_string = response.content.decode('utf-8') # Initially in bytes
        lines = response_string.strip().split('\r\n')
        data_lines = lines[3:]

        database_names = set()
        for line in data_lines:
            parts = [part.strip() for part in line.split('|')]
            if parts and parts[-1] == '':
                parts = parts[:-1]
            if len(parts) == 6:
                database_names.add(parts[0])

        return database_names
    except requests.exceptions.RequestException as e:
        raise RequestException(e)


def connect_to_db(edgelake_node_url, db_name, user, password, ip, port):
    """
    Connect to the database on the given EdgeLake node.

    :param edgelake_node_url: The URL of the EdgeLake node with the database to connect.
    :param command: The Anylog command to connect databases.
    """
    # TODO: add db types if necessary
    command = (f"connect dbms {db_name} where type = psql"
                + f" and user = {user} and password = {password}"
                + f" and ip = {ip} and port = {port} and memory = true")

    headers = {
        'User-Agent': 'AnyLog/1.23',
        'command': command,
    }
    try:
        # Send the POST request
        response = requests.post(edgelake_node_url, headers=headers)

        # Raise an HTTPError if the response code indicates failure
        response.raise_for_status()

    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"Unable to connect to database: {e}")

def get_all_databases(edgelake_node_url):
    """
    Gets all databases that the specified EdgeLake node is connected to.

    :param edgelake_node_url: The URL of the EdgeLake node to fetch the databases list.
    :return: Set of all the connected databases.
    :rtype: set()
    """
    command = "get databases"
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'command': command,
    }

    try:
        # Send the POST request
        response = requests.get(edgelake_node_url, headers=headers)

        # Raise an HTTPError if the response code indicates failure
        response.raise_for_status()

        # Parsing response content
        response_string = response.content.decode('utf-8') # Initially in bytes
        lines = response_string.strip().split('\r\n')
        data_lines = lines[3:]

        database_names = set()
        for line in data_lines:
            parts = [part.strip() for part in line.split('|')]
            if parts and parts[-1] == '':
                parts = parts[:-1]
            if len(parts) == 6:
                database_names.add(parts[0])

        return database_names
    except requests.exceptions.RequestException as e:
        raise RequestException(e)


def connect_to_db(edgelake_node_url, db_name, user, password, ip, port):
    """
    Connect to the database on the given EdgeLake node.

    :param edgelake_node_url: The URL of the EdgeLake node with the database to connect.
    :param command: The Anylog command to connect databases.
    """
    # TODO: add db types if necessary
    command = (f"connect dbms {db_name} where type = psql"
                + f" and user = {user} and password = {password}"
                + f" and ip = {ip} and port = {port} and memory = true")

    headers = {
        'User-Agent': 'AnyLog/1.23',
        'command': command,
    }
    try:
        # Send the POST request
        response = requests.post(edgelake_node_url, headers=headers)

        # Raise an HTTPError if the response code indicates failure
        response.raise_for_status()

    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"Unable to connect to database: {e}")


def fetch_data_from_db(edgelake_node_url, query):
    """
    Fetch data from the database using an HTTP request with the provided SQL query.

    :param query: The SQL query to fetch the data.
    :type query: str
    :return: Parsed JSON response containing the fetched data.
    :rtype: dict
    """
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'command': query,
    }

    try:
        # Send the GET request
        response = requests.get(edgelake_node_url, headers=headers)

        # Raise an HTTPError if the response code indicates failure
        response.raise_for_status()

        # Parse the response JSON
        return response.json()
    except requests.exceptions.RequestException as e:
        raise IOError(f"Failed to execute SQL query: {e}")
    except json.JSONDecodeError:
        raise ValueError("The response from the request is not valid JSON.")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to connect; used to determine the local IP
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


if __name__ == '__main__':
    el_url = 'http://192.168.65.3:32049'
    data = f'''<my_policy = {{"test-policy" : {{
                                    "node" : "A",
                                    "ip_port": "10.0.0",
                                    "trained_params_dbms": "my_db",
                                    "trained_params_table": "my_table",
                                    "trained_params_filename": "file.json"
                }} }}>'''
    response = insert_policy(el_url, data)
    print(response.status_code)
    # response = force_insert_policy(el_url, data)
    # print(response.status_code)
    # response = force_insert_policy(el_url, data)
    # print(response.status_code)
    # response = force_insert_policy(el_url, data)
    # print(response.status_code)

    response = insert_policy(el_url, data)
    print(response.status_code)
    # response = delete_policy(el_url, "f6df879142f006e6e4fc8e14114b63e2")
    # print(response.status_code)
    # response = insert_policy(el_url, data)
    # print(response.status_code)
    # response = delete_policy(el_url, "f6df879142f006e6e4fc8e14114b63e2")
    # print(response.status_code)
    # response = insert_policy(el_url, data)
    # print(response.status_code)