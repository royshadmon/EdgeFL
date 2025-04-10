"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""


import os
import time

import docker
# Add files to MongoDB through EdgeLake

import requests
import sys
import tarfile

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


def copy_file_to_container(tmp_dir, container_name, src_path, dest_path):
    """
    Copies a file from the host to a container.

    :param container_name: Name or ID of the container
    :param src_path: Absolute path of the source file on the host
    :param dest_path: Destination path in the container (directory or full path)
    """
    client = docker.from_env()
    container = client.containers.get(container_name)

    # Create a tar archive for the file
    with tarfile.open(f"{tmp_dir}/temp.tar", mode="w") as tar:
        tar.add(src_path, arcname=os.path.basename(src_path))

    # Open the tar file and send it to the container
    with open(f"{tmp_dir}/temp.tar", "rb") as tar_file:
        container.put_archive(os.path.dirname(dest_path), tar_file)

    # Clean up the temporary tar file
    os.remove(f"{tmp_dir}/temp.tar")
    # print(f"Copied {src_path} to {container_name}:{dest_path}")
    # print(f"Received model params")

def copy_file_from_container(tmp_dir, container_name, src_path, dest_path):
    """
    Copies a file from a container to the host machine.

    :param container_name: Name or ID of the container
    :param src_path: Path of the source file inside the container
    :param dest_path: Destination path on the host (directory or full path)
    """
    client = docker.from_env()
    container = client.containers.get(container_name)
    try:
        # Step 1: Get file size inside the container for verification
        exec_result = container.exec_run(f"stat -c %s {src_path}")
        if exec_result.exit_code != 0:
            print(f"❌ Error: Could not get file size for {src_path} inside the container.")
            return False
        container_file_size = int(exec_result.output.decode().strip())

        # Step 2: Get the file from the container as a tar stream
        tar_stream, _ = container.get_archive(src_path)

        # Step 3: Extract the tar stream to the host
        with open(f"{tmp_dir}/temp.tar", "wb") as temp_tar:
            for chunk in tar_stream:
                temp_tar.write(chunk)
            temp_tar.flush()
            os.fsync(temp_tar.fileno()) # Ensure data is physically written to disk

        # Step 4: Extract tar file
        with tarfile.open(f"{tmp_dir}/temp.tar", mode="r") as tar:
            # Extract the file to the desired host location
            tar.extractall(path=os.path.dirname(dest_path), filter='fully_trusted')

        # Step 5: Move extracted file to final destination
        extracted_file = os.path.join(os.path.dirname(dest_path), os.path.basename(src_path))
        os.rename(extracted_file, dest_path) # rename file

        # Step 6: Verify file integrity
        for _ in range(5):
            if os.path.exists(dest_path) and os.path.getsize(dest_path) == container_file_size:
                print(f"✅ Successfully copied {src_path} from {container_name} to {dest_path}")
                os.remove(f"{tmp_dir}/temp.tar")  # Cleanup temporary tar file
                return True
            time.sleep(0.5)
        print(
            f"❌ Verification failed: Expected {container_file_size} bytes, Got {os.path.getsize(dest_path) if os.path.exists(dest_path) else 'Missing'}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up the temporary tar file
        if os.path.exists(f"{tmp_dir}/temp.tar"):
            os.remove(f"{tmp_dir}/temp.tar")


def read_file(edgelake_node_url, file_path, dest, ip_port):
    filename = file_path.split('/')[-1]
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        # 'command': f'file get (dbms={dbms} and table={table} and id={filename.split("/")[-1]}) {dest}',
        'command': f'run client {ip_port} file get {file_path} {dest}'
        # 'destination': ip_port
    }

    # print(f"FILE GET COMMAND: headers: {headers['command']}")
    try:
        response = requests.post(edgelake_node_url, headers=headers, data='')
        return response
    except:
        errno, value = sys.exc_info()[:2]
        print(f'Error: {errno}: {value}')



def read_file_mongo(edgelake_node_url, dbms, table, filename, dest, ip_port):

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