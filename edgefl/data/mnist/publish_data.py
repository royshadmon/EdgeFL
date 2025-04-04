import argparse
import json
import os.path
import base64

import requests

def __compress_file(file_path:str):
    base64_bytes = None
    try:
        with open(file_path, 'rb') as f:
            base64_bytes = base64.b64encode(f.read())
    except Exception as error:
        raise Exception(f"Failed to read / compress file {file_path} (Error: {error}) ")
    return base64_bytes.decode('utf-8')

def post_cmd(conn:str, headers:dict, payload:str=None):
    """
    Publish into Operator node via POST
    """
    try:
        response = requests.post(url=f"http://{conn}", headers=headers, data=payload)
        response.raise_for_status()
    except Exception as error:
        raise Exception(f"Failed to run POST against {conn} (Error: {error})")

def create_mapping(conn:str, policy_id:str, db_name:str, table_name:str):
    """
    Create mapping policy
    :url:
        https://github.com/AnyLog-co/documentation/blob/master/image%20mapping.md
    :note:
        when declaring a policy - make sure the policy DNE beforehand
    :args:
        conn:str - REST connection
        db_name:str - logical database name
        table_name:str - logical table name
    :params:
        mapping_policy:dict - mapping policy to use
        new_policy:str - serialized mapping policy
        headers:dict -REST headers
    """
    mapping_policy = {
        "mapping": {
            "id": policy_id,
            "dbms": db_name,
            "table": table_name,
            "schema": {
                "timestamp": {
                    "type": "timestamp",
                    "default": "now()"
                },
                "image_name": {
                    "type": "string",
                    "default": "",
                    "bring": "[image_name]"
                },
                "image": {
                    "blob": True,
                    "bring": "[image]",
                    "extension": "gz",
                    "apply": "base64decoding",
                    "hash": "md5",
                    "type": "varchar"
                },
                "label_name": {
                    "type": "string",
                    "default": "",
                    "bring": "[label_name]"
                },
                "label": {
                    "blob": True,
                    "bring": "[image]",
                    "extension": "gz",
                    "apply": "base64decoding",
                    "hash": "md5",
                    "type": "varchar"
                }
            }
        }
    }

    new_policy = f"<new_policy={json.dumps(mapping_policy)}>"
    headers = {
        "command": "blockchain insert where policy=!new_policy and local=true and master=!ledger_conn",
        "User-Agent": "AnyLog/1.23"
    }

    post_cmd(conn=conn, headers=headers, payload=new_policy)

def run_msg_client(conn:str, policy_id:str, topic:str):
    headers = {
        "command": "run msg client where broker=rest and log=false and user-agent=anylog and topic=(name=mnist and policy=mnist)",
        "User-Agent": "AnyLog/1.23"
    }

    post_cmd(conn=conn, headers=headers, payload=None)

def publish_data(conn:str, topic:str, image_path:str, label_path:str):
    headers = {
        'command': 'data',
        'topic': topic,
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain'
    }

    image_file = os.path.basename(image_path)
    label_file = os.path.basename(label_path)
    image_content = __compress_file(image_path)
    label_content = __compress_file(label_path)

    payload = json.dumps(
        {
            "image_name": image_file,
            "image": image_content,
            "label_name": label_file,
            "label": label_content
        }
    )

    post_cmd(conn=conn, headers=headers, payload=payload)

def main():
    parse = argparse.ArgumentParser()
    parse.add_argument('conn', type=str, default='74.207.235.89:32149')
    parse.add_argument('--policy-id', type=str, default='mnist')
    parse.add_argument('--topic', type=str, default='mnist')
    parse.add_argument('--db-name', type=str, default='new_company')
    parse.add_argument('--table-name', type=str, default='mnist')

    parse.add_argument('--image', type=str, default=None, required=True)
    parse.add_argument('--label', type=str, default=None, required=True)
    args = parse.parse_args()

    args.image = os.path.expanduser(os.path.expandvars(args.image))
    if not os.path.isfile(args.image):
        raise FileNotFoundError(args.image)
    args.label = os.path.expanduser(os.path.expandvars(args.label))
    if not os.path.isfile(args.label):
        raise FileNotFoundError(args.label)

    # publish mapping
    # create_mapping(conn='74.207.235.89:32149', policy_id=args.policy_id, db_name='new_company', table_name='mnist')
    # run_msg_client(conn=args.conn, policy_id=args.policy_id, topic=args.topic)

    publish_data(conn=args.conn, topic=args.topic, image_path=args.image, label_path=args.label)
    # payload = {
    #     "image_name": image_file,
    #     "image": image_content,
    #     "label_name": label_file,
    #     "label": label_content
    # }
    #
    # post_cmd(conn=args.conn, headers=)

if __name__ == '__main__':
    main()