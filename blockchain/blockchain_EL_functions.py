import requests
import socket

def insert_policy(el_url, policy):
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain',
        'command': 'blockchain insert where policy = !my_policy and local = true and blockchain = optimism'
    }

    response = requests.post(el_url, headers=headers, data=policy)
    return response


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to connect; used to determine the local IP
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip