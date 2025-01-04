

# Add files to MongoDB through EdgeLake

import requests
import sys

def write_file(edgelake_node_url, dbms, table, filename):
    lst = filename.split('/')
    # lst[-1] = f'{dbms}.{table}.{lst[-1]}'
    filename = ('/').join(lst)

    # headers = {
    #     'User-Agent': 'AnyLog/1.23',
    #     'Content-Type': 'text/plain',
    #     'command': f'file store where dbms = {dbms} and table = {table} and dest = 1-replica-node1.pkl'
    # }
    # with open("/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/node1/1-replica-node1.pkl", 'rb') as f:
    #     response = requests.post(edgelake_node_url, headers=headers, data=f)

    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'application/octet-stream',  # Specify binary content
        'command': f'file store where dbms = {dbms} and table = {table} and dest = {filename.split("/")[-1]}'
    }
    with open(filename, 'rb') as f:
        binary_data = f.read()
        response = requests.post(edgelake_node_url, headers=headers, data=binary_data)
    return response



def read_file(edgelake_node_url, dbms, table, filename, dest, ip_port):
    # headers = {
    #     'User-Agent': 'AnyLog/1.23',
    #     'Content-Type': 'text/plain',
    #     'command': f'file retrieve where dbms = {dbms} and table = {table} and id = {filename} and dest = {dest}'
    # }

    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': f'file get (dbms={dbms} and table={table} and id={filename.split("/")[-1]}) {dest}',
        'destination': ip_port
    }

    try:
        response = requests.post(edgelake_node_url, headers=headers, data='')
        return response
    except:
        errno, value = sys.exc_info()[:2]
        print(f'Error: {errno}: {value}')


if __name__ == '__main__':
    write_file(f"http://192.168.1.118:32049", "blobs_admin", "my_table", "/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/node1/1-replica-node1.pkl")
    read_file(f"http://192.168.1.118:32049", "blobs_admin", "my_table", "1-replica-node1.pkl", "/Users/roy/Github-Repos/Anylog-Edgelake-CSE115D/blockchain/file_write/aggregator/1-replica-node1.pkl", None)
