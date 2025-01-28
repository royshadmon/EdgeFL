import os
import docker
# Add files to MongoDB through EdgeLake

import requests
import sys

def write_file(edgelake_node_url, dbms, table, filename):
    lst = filename.split('/')
    # lst[-1] = f'{dbms}.{table}.{lst[-1]}'
    filename = ('/').join(lst)

    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'application/octet-stream',  # Specify binary content
        'command': f'file store where dbms = {dbms} and table = {table} and dest = {filename.split("/")[-1]}'
    }

    with open(filename, 'rb') as f:
        binary_data = f.read()
        response = requests.post(edgelake_node_url, headers=headers, data=binary_data)
    return response


def create_directory_in_container(container_name, directory_path):
    """
    Create a directory inside a Docker container.

    Args:
        container_name (str): Name or ID of the container.
        directory_path (str): Path of the directory to create inside the container.
    """
    client = docker.from_env()
    container = client.containers.get(container_name)

    # Run the `mkdir` command inside the container
    command = f"mkdir -p {directory_path}"
    exit_code, output = container.exec_run(command)

    if exit_code == 0:
        print(f"Directory '{directory_path}' created successfully in container '{container_name}'.")
    else:
        print(f"Failed to create directory. Error: {output.decode('utf-8')}")

def copy_to_container(container_name, source_path, dest_path):
    """
    Copy a file from the host to a container.

    Args:
        container_name (str): Name or ID of the container.
        source_path (str): Path of the file on the host.
        dest_path (str): Destination path inside the container.
    """
    client = docker.from_env()
    container = client.containers.get(container_name)

    # Open the source file
    with open(source_path, 'rb') as file_data:
        # Use the container's put_archive method to copy the file
        container.put_archive(dest_path, file_data.read())

    print(f"Copied {source_path} to {container_name}:{dest_path}")

def copy_from_container(container_name, source_path, destination_path):
    client = docker.from_env()
    container = client.containers.get(container_name)

    # Open the file or directory from the container
    tar_stream, _ = container.get_archive(source_path)

    # Save the tar stream to a local file
    with open("temp.tar", "wb") as f:
        for chunk in tar_stream:
            f.write(chunk)

    # Extract the tar file to the destination path
    import tarfile
    with tarfile.open("temp.tar") as tar:
        tar.extractall(path=destination_path)


def read_file(edgelake_node_url, file_path, dest, ip_port):
    filename = file_path.split('/')[-1]
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        # 'command': f'file get (dbms={dbms} and table={table} and id={filename.split("/")[-1]}) {dest}',
        'command': f'run client {ip_port} file get {file_path} {dest}'
        # 'destination': ip_port
    }

    print(f"FILE GET COMMAND: headers: {headers['command']}")
    try:
        response = requests.post(edgelake_node_url, headers=headers, data='')
        return response
    except:
        errno, value = sys.exc_info()[:2]
        print(f'Error: {errno}: {value}')



def read_file_mongo(edgelake_node_url, dbms, table, filename, dest, ip_port):
    # headers = {
    #     'User-Agent': 'AnyLog/1.23',
    #     'Content-Type': 'text/plain',
    #     'command': f'file retrieve where dbms = {dbms} and table = {table} and id = {filename} and dest = {dest}'
    # }

    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        # 'command': f'file get (dbms={dbms} and table={table} and id={filename.split("/")[-1]}) {dest}',
        'command': f'run client {ip_port} file get (dbms={dbms} and table={table} and id={filename.split("/")[-1]}) {dest}'
        # 'destination': ip_port
    }

    print(f"FILE GET COMMAND: headers: {headers['command']}")
    try:
        response = requests.post(edgelake_node_url, headers=headers, data='')
        return response
    except:
        errno, value = sys.exc_info()[:2]
        print(f'Error: {errno}: {value}')


if __name__ == '__main__':
    file_write_destination = os.getenv("FILE_WRITE_DESTINATION")
    # write_file(f"http://192.168.1.118:32049", "blobs_admin", "my_table",
    #            f"{file_write_destination}/node1/1-replica-node1.pkl")
    response = read_file(f"http://192.168.1.118:32048", "blobs_winniio_fl", "node_model_updates", "1-replica-node3.pkl", f"{file_write_destination}/aggregator/1-replica-node1.pkl", "192.53.121.36:32148")
    print(response.status_code)
