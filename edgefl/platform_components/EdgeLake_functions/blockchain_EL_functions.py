"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""


from asyncio import sleep

import requests
import socket
import json

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
        print(response.status_code)


        response = requests.get(el_url, headers=headers)
        retrieved_policy = json.loads(response.content.decode('utf-8'))

        if retrieved_policy:
            return True

        return False


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