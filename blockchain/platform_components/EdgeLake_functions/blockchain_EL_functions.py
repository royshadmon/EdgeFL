import requests
import socket
import json

def insert_policy(el_url, policy):
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': 'blockchain insert where policy = !my_policy and local = true and blockchain = optimism'
    }

    response = requests.post(el_url, headers=headers, data=policy)
    return response

def delete_policy(el_url, policy_id):
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': f'blockchain delete policy where id = {policy_id} and local = true and blockchain = optimism'
    }

    response = requests.post(el_url, headers=headers, data=None)
    return response

def force_insert_policy(el_url, policy):

    response = insert_policy(el_url, policy)
    if response.status_code == 200:
        print(f'Successfully inserted policy {policy}')
        return response
    else:
        print(f'Deleting inserted policy {policy}')
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
        response = requests.get(el_url, headers=headers)
        retrieved_policy = json.loads(response.content.decode('utf-8'))
        policy_id = retrieved_policy.get(list(retrieved_policy.keys())[0]).get('id')

        response = delete_policy(el_url, policy_id)
        response = insert_policy(el_url, policy)
        if response.status_code == 200:
            print("SUCCESS INSERT AFTER DELETING")
            return response
        else:
            print("Failure")

    return response

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
    el_url = 'http://192.168.1.125:32049'
    data = f'''<my_policy = {{"a-1" : {{
                                    "node" : "A",
                                    "ip_port": "10.0.0",
                                    "trained_params_dbms": "my_db",
                                    "trained_params_table": "my_table",
                                    "trained_params_filename": "file.json"
                }} }}>'''
    response = force_insert_policy(el_url, data)
    response2 = force_insert_policy(el_url, data)