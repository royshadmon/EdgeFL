import argparse
import requests
import json
import torch
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

    # Build per-class index lists (shuffled within each class for variety)
    num_classes = 10
    train_by_class = {c: [] for c in range(num_classes)}
    for i, label in enumerate(train_dataset.targets.tolist()):
        train_by_class[label].append(i)
    for c in range(num_classes):
        perm = torch.randperm(len(train_by_class[c])).tolist()
        train_by_class[c] = [train_by_class[c][p] for p in perm]

    test_by_class = {c: [] for c in range(num_classes)}
    for i, label in enumerate(test_dataset.targets.tolist()):
        test_by_class[label].append(i)
    for c in range(num_classes):
        perm = torch.randperm(len(test_by_class[c])).tolist()
        test_by_class[c] = [test_by_class[c][p] for p in perm]

    samples_per_class_train = TRAIN_SAMPLES_PER_ROUND // num_classes
    samples_per_class_test  = max(1, TEST_SAMPLES_PER_ROUND // num_classes)
    train_class_pos = {c: 0 for c in range(num_classes)}
    test_class_pos  = {c: 0 for c in range(num_classes)}

    for round_num in range(1, args.num_rounds + 1):
        # Pick exactly samples_per_class_train from each class for training
        train_indices = []
        for c in range(num_classes):
            start = train_class_pos[c]
            end   = start + samples_per_class_train
            train_indices.extend(train_by_class[c][start:end])
            train_class_pos[c] = end
        perm = torch.randperm(len(train_indices)).tolist()
        train_indices = [train_indices[p] for p in perm]
        train_images = train_dataset.data[train_indices]
        train_labels = train_dataset.targets[train_indices]

        json_train = [{"image": json.dumps(img.numpy().flatten().tolist()), "label": int(label), "round_number": round_num} for img, label in zip(train_images, train_labels)]
        header = create_header(db_name=args.db_name, table_name="mnist_train")

        print(f"Inserting to mnist_train (round {round_num})")
        try:
            __put_data(conn=args.conn, headers=header, payload=json_train)
        except Exception as error:
            raise Exception

        # Pick exactly samples_per_class_test from each class for testing
        test_indices = []
        for c in range(num_classes):
            start = test_class_pos[c]
            end   = start + samples_per_class_test
            test_indices.extend(test_by_class[c][start:end])
            test_class_pos[c] = end
        perm = torch.randperm(len(test_indices)).tolist()
        test_indices = [test_indices[p] for p in perm]
        test_images = test_dataset.data[test_indices]
        test_labels = test_dataset.targets[test_indices]

        json_test = [{"image": json.dumps(img.numpy().flatten().tolist()), "label": int(label), "round_number": round_num} for img, label in zip(test_images, test_labels)]
        header = create_header(db_name=args.db_name, table_name="mnist_test")

        print(f"Inserting to mnist_test (round {round_num})")
        try:
            __put_data(conn=args.conn, headers=header, payload=json_test)
        except Exception as error:
            raise Exception



if __name__ == '__main__':
    main()

