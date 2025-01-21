import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from ibmfl.data.data_handler import DataHandler

# from logging import getLogger
# logger = getLogger(__name__)

# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from pipeline import run_pipeline


class LSTMOneDataLoader(TensorFlowDataLoader):

    def __init__(self, node_name):
        """
        Initialize.

        Args:
            data_path: File path for the dataset
            batch_size (int): The batch size for the data loader
            **kwargs: Additional arguments, passed to super init and load_mnist_shard
        """
        super().__init__()

        X_train, y_train, X_valid, y_valid = load_collaborator_data(room_num=int(data_path))

        self.X_train = X_train
        self.y_train = y_train
        self.X_valid = X_valid
        self.y_valid = y_valid


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
