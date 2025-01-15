import base64
import cv2
import datetime
import json
import numpy as np
from torchvision import datasets
import requests

NUM_NODES = 2
NUM_ROUNDS = 12
TRAIN_SAMPLES_PER_ROUND = 50
TEST_SAMPLES_PER_ROUND = 10

NODE_NAME = "node%s"
CONN = '10.0.0.131:32149'
# CONN = "127.0.0.1:32549"

def __image_to_base64(image):
    """Convert a PyTorch image tensor to a Base64 string."""
    # Convert to NumPy array
    image_np = image.numpy()
    # Ensure the image has three dimensions (H, W, C)
    if len(image_np.shape) == 2:  # Grayscale images
        image_np = np.expand_dims(image_np, axis=-1)
    # Encode to JPEG format
    _, buffer = cv2.imencode('.jpg', image_np)
    # Convert to Base64
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    return image_base64


def insert_round_data(table_name, round_num, images, labels, data_type, db_name="mnist_fl"):
    """Generate JSON data for a specific round instead of inserting into the database."""
    try:
        # Process in batches
        BATCH_SIZE = 10
        result = []

        for i in range(0, len(images), BATCH_SIZE):
            batch_images = images[i:i + BATCH_SIZE]
            batch_labels = labels[i:i + BATCH_SIZE]

            for img, lbl in zip(batch_images, batch_labels):
                # img_array = img.numpy().flatten().tolist()
                result.append(json.dumps({
                    "dbms": db_name,
                    "table": table_name,
                    "timestamp": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'),
                    "round_number": round_num,
                    "data_type": data_type,
                    "image": img.numpy().flatten().tolist(),
                    "label": int(lbl)

                }))

        # print(f"Prepared {len(images)} {data_type} samples for round {round_num} in {table_name}")
        return result

    except Exception as e:
        raise Exception(f"Error preparing data: {str(e)}")


def publish_data(data):
    headers = {
        'command': 'data',
        'topic': "ai-mnist-fl",
        'User-Agent': 'AnyLog/1.23',
        'Content-Type': 'text/plain'
    }
    for result in data:
        try:
            r = requests.post(url=f"http://{CONN}", headers=headers, data=result)
        except Exception as error:
            raise Exception(f"Failed to POST data against {CONN} (Error: {error})")
        else:
            if not 200 <= int(r.status_code) < 300:
                raise ConnectionError(f"Failed to POST data against {CONN} (Error: {r.status_code})")


def run_rounds():
    train_dataset = datasets.MNIST('data', train=True, download=True)
    test_dataset = datasets.MNIST('data', train=False, download=True)
    train_idx = 0
    test_idx = 0

    for node in range(1, NUM_NODES + 1):
        node_name = NODE_NAME % node

        for round_num in range(1, NUM_ROUNDS + 1):
            train_end = train_idx + TRAIN_SAMPLES_PER_ROUND
            train_images = train_dataset.data[train_idx:train_end]
            train_labels = train_dataset.targets[train_idx:train_end]
            train_images_output = insert_round_data(table_name=f"train_{node_name}", round_num=round_num,
                                                    images=train_images, labels=train_labels, data_type='train')
            train_idx = train_end

            # Insert test data for this round
            test_end = test_idx + TEST_SAMPLES_PER_ROUND
            test_images = test_dataset.data[test_idx:test_end]
            test_labels = test_dataset.targets[test_idx:test_end]
            test_images_output = insert_round_data(table_name=f"test_{node_name}", round_num=round_num,
                                                   images=test_images, labels=test_labels, data_type='test')
            test_idx = test_end


            # print(train_images_output)
            publish_data(data=train_images_output)
            # print(test_images_output)


if __name__ == '__main__':
    run_rounds()



