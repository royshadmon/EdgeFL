import argparse
import requests
import json
from torchvision import datasets
import time

def __put_data(conn:str, payload:(list or str or dict), headers:dict):
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
        for row in payload:
            response = requests.put(url=f"http://{conn}", data=json.dumps(row), headers=headers)
            response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed to execute POST against {conn} (Error: {e})")


def create_header(db_name:str, table_name:str):
    header = {
        "type": "json",
        "dbms": db_name,
        "table": table_name,
        "mode": "streaming",
        "Content-Type": "text/plain"
    }
    return header




def main():
    parse = argparse.ArgumentParser()
    parse.add_argument('conn', type=str, default=None, help='REST connection information')
    # parse.add_argument('image_file', type=__validate_file, default=None, help='image gz file')
    # parse.add_argument('label_file', type=__validate_file, default=None, help='label gz file')
    parse.add_argument('--db-name', type=str, default='mnist', help='logical database name')
    parse.add_argument('--num-rounds', type=int, default=20, help='Number of training rounds to add')
    parse.add_argument('--num-rows', type=int, default=50, help='')
    # parse.add_argument('--test-split', type=int, default=0.2, help='')

    # create tsd_info
    args = parse.parse_args()

    for cmd_type in ['drop', 'create']:
        try:
            response = requests.post(f'http://{args.conn}', headers={'command': f"{cmd_type} table tsd_info where dbms=almgm",
                                                   'User-Agent': 'AnyLog/1.23'})
            response.raise_for_status()
        except Exception as e:
            print("Failed to execute POST against {args.conn} (Error: {e})")
            # raise Exception(f"Failed to execute POST against {args.conn} (Error: {e})")


    TRAIN_SAMPLES_PER_ROUND = int(args.num_rows)
    TEST_SAMPLES_PER_ROUND = int(TRAIN_SAMPLES_PER_ROUND * 0.2)

    train_dataset = datasets.MNIST('..', train=True, download=True)
    test_dataset = datasets.MNIST('..', train=False, download=True)

    train_idx = 0
    test_idx = 0
    for round_num in range(1, args.num_rounds + 1):
        train_end = train_idx + TRAIN_SAMPLES_PER_ROUND
        train_images = train_dataset.data[train_idx:train_end]
        train_labels = train_dataset.targets[train_idx:train_end]

        json_train = [{"image": img.numpy().flatten().tolist(), "label": int(label), "round_number": round_num} for img, label in zip(train_images, train_labels)]
        # json_train = json.dumps(rows)
        header = create_header(db_name=args.db_name, table_name="mnist_train")

        print("Inserting to mnist_train")
        try:
            __put_data(conn=args.conn, headers=header, payload=json_train)
        except Exception as error:
            raise Exception

        test_end = test_idx + TEST_SAMPLES_PER_ROUND
        test_images = test_dataset.data[test_idx:test_end]
        test_labels = test_dataset.targets[test_idx:test_end]

        json_test = [{"image": img.numpy().flatten().tolist(), "label": int(label), "round_number": round_num} for img, label in
                zip(test_images, test_labels)]
        # json_test = json.dumps(rows)
        header = create_header(db_name=args.db_name, table_name="mnist_test")

        print("Inserting to mnist_test")
        try:
            __put_data(conn=args.conn, headers=header, payload=json_test)
        except Exception as error:
            raise Exception



if __name__ == '__main__':
    main()

