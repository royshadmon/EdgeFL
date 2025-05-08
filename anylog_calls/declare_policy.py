import json
import requests
from tensorflow.tools.pip_package.v2.setup import headers

POLICY_ID = "ai-mnist-fl"
POLICY = {
    "mapping": {
        "id": POLICY_ID,
        "dbms": "bring [dbms]",
        "table": "bring [table]",
        "schema": {
            "timestamp": {
                "type": "timestamp",
                "default": "now()",
                "bring": "[timestamp]"
            },
            "round_number": {
                "type": "int",
                "default": -1,
                "bring": "[round_number]"
            },
            "data_type": {
                "type": "string",
                "default": "train",
                "bring": "[data_type]"
            },
            "label": {
                "type": "int",
                "default": 1,
                "bring": "[label]"
            },
            "file": {
                "blob": True,
                "bring": "[image]",
                "extension": "png",
                "apply": "opencv",
                "hash": "md5",
                "type": "varchar"
            }
        }
    }
}
CONN = '10.0.0.131:32149'
LEDGER_CONN = '10.0.0.131:32048'


def get_policy():
    headers = {
        "command": f"blockchain get mapping where id={POLICY} bring.count",
        "User-Agent": "AnyLog/1.23"
    }
    status = None
    try:
        r = requests.get(url=f"http://{CONN}", headers=headers)
    except Exception as error:
        raise Exception(f"Failed to get policy from {CONN} (Error: {error})")
    else:
        if not 200 <= int(r.status_code) < 300:
            raise ConnectionError(f"Failed to get policy from {CONN} (Error: {r.status_code})")
        status = True if r.text == 1 else False
    return status


def declare_policy():
    headers = {
        "command": "blockchain insert where policy=!new_policy and local=true and master=!ledger_conn",
        "User-Agent": "AnyLog/1.23",
        "destination": LEDGER_CONN
    }

    policy = f"<new_policy={json.dumps(POLICY)}>"
    try:
        r = requests.post(url=f"http://{CONN}", headers=headers, data=policy)
    except Exception as error:
        raise Exception(f"Failed to declare policy via {CONN} (Error: {error})")
    else:
        if not 200 <= int(r.status_code) < 300:
            raise ConnectionError(f"Failed to declare policy via {CONN} (Error: {r.status_code})")

def declare_mapping():
    command = f"""
    run msg client where broker=rest and port=!anylog_rest_port and user-agent=anylog and log=false and topic=(
        name={POLICY_ID} and
        policy={POLICY_ID}
    )
    """.replace("\n","")
    headers = {
        "command": command,
        "User-Agent": "AnyLog/1.23"
    }


    try:
        r = requests.post(url=f"http://{CONN}", headers=headers)
    except Exception as error:
        raise Exception(f"Failed to declare MQTT client via {CONN} (Error: {error})")
    else:
        if not 200 <= int(r.status_code) < 300:
            raise ConnectionError(f"Failed to declare MQTT client via {CONN} (Error: {r.status_code})")


def main():
    status = get_policy()
    if status is False:
        declare_policy()
    declare_mapping()


if __name__ == '__main__':
    main()