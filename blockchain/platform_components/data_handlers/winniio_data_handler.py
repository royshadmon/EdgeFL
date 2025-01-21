import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from ibmfl.data.data_handler import DataHandler

from blockchain_EL_functions import fetch_data_from_db


# from logging import getLogger
# logger = getLogger(__name__)

# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from pipeline import run_pipeline


class WinniioDataHandler(DataHandler):

    def __init__(self, node_name):
        """
        Initialize.

        Args:
            data_path: File path for the dataset
            batch_size (int): The batch size for the data loader
            **kwargs: Additional arguments, passed to super init and load_mnist_shard
        """
        super().__init__()

        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        X_train, y_train, X_valid, y_valid = self.load_dataset(node_name, 1)

        self.X_train = X_train
        self.y_train = y_train
        self.X_valid = X_valid
        self.y_valid = y_valid

    def load_dataset(self, node_name, round_number):

        """
        Loads the training and testing datasets by running SQL queries to fetch data.

        :param nb_points: Number of data points to fetch for training and testing datasets.
        :type nb_points: int
        :return: Training and testing datasets as NumPy arrays.
        :rtype: tuple
        """

        # these queries will depend on how we've uploaded mnist data and use round_number param in query
        # we are pulling batched data for each round
        # query_train = f"SELECT * FROM {node_name}"
        # print(query_train)
        # query_test = f"SELECT * FROM test-{node_name}-{round_number}"

        db_name = os.getenv("PSQL_DB_NAME")
        query_train = f"sql {db_name} SELECT round_number, data_type, actuatorState, co2Value, eventCount, humidity, switchStatus, temperature, day, time, month, date, label FROM node_{node_name} WHERE round_number = {round_number} AND data_type = 'train'"
        query_test = f"sql {db_name} SELECT round_number, data_type, actuatorState, co2Value, eventCount, humidity, switchStatus, temperature, day, time, month, date, label FROM node_{node_name} WHERE round_number = {round_number} AND data_type = 'test'"

        try:
            train_data = fetch_data_from_db(self.edgelake_node_url, query_train)
            test_data = fetch_data_from_db(self.edgelake_node_url, query_test)

            # Assuming the data is returned as dictionaries with keys 'x' and 'y'
            query_train_result = np.array(train_data["Query"])
            x_train_images = []
            y_train_labels = []
            for i in range(len(query_train_result)):
                x_train_image_np_array = np.array(ast.literal_eval(query_train_result[i]['image']))
                y_train_label = query_train_result[i]['label']
                x_train_images.append(x_train_image_np_array)
                y_train_labels.append(y_train_label)

            y_train_label_final = np.array(y_train_labels, dtype=np.int64)

            query_test_result = np.array(test_data["Query"])
            x_test_images = []
            y_test_labels = []
            for i in range(len(query_test_result)):
                x_test_image_np_array = np.array(ast.literal_eval(query_test_result[i]['image']))
                x_test_images.append(x_test_image_np_array)
                y_test_label = query_test_result[i]['label']
                y_test_labels.append(y_test_label)

            img_rows, img_cols = 28, 28
            x_train_images_final = np.array(x_train_images, dtype=np.float32).reshape(-1, 1, img_rows, img_cols)
            x_test_images_final = np.array(x_test_images, dtype=np.float32).reshape(-1, 1, img_rows, img_cols)

            print("Train data shape after loading and reshaping:", x_train_images_final.shape)

            y_test_label_final = np.array(y_test_labels, dtype=np.int64)
            print("Test data shape after loading:", x_test_images_final.shape)

        except Exception as e:
            raise IOError(f"Error fetching datasets: {str(e)}")

        return (x_train_images_final, y_train_label_final), (x_test_images_final, y_test_label_final)


def load_collaborator_data(room_num):
    df = run_pipeline(room_num)

    # df = pd.read_csv(f'data/{room_num}.csv')

    df['future_temp'] = df['temperature'].shift(-2)
    df.dropna(inplace=True)

    X = df[
        ['actuatorState', 'co2Value', 'eventCount', 'humidity', 'switchStatus', 'temperature', 'day', 'time', 'month',
         'date']]
    y = df['future_temp']

    n_train_rows = int(0.8 * len(df))

    X_train = X.iloc[:n_train_rows, :]
    y_train = y.iloc[:n_train_rows].values

    X_test = X.iloc[n_train_rows:, :]
    y_test = y.iloc[n_train_rows:].values

    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()

    X1_scaled = scaler_X.fit_transform(X_train)
    X2_scaled = scaler_X.transform(X_test)

    y1_scaled = scaler_y.fit_transform(y_train.reshape(-1, 1))
    y2_scaled = scaler_y.transform(y_test.reshape(-1, 1))

    time_steps = 1

    X_train, y_train = create_sequences(X1_scaled, y1_scaled, time_steps)
    X_test, y_test = create_sequences(X2_scaled, y2_scaled, time_steps)

    return X_train, y_train, X_test, y_test


def create_sequences(X, y=0, time_steps=1):
    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        Xs.append(X[i:i + time_steps])
        ys.append(y[i + time_steps])
    return np.array(Xs), np.array(ys)
