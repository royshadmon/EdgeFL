"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""


import ast
import os
import logging

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from ibmfl.data.data_handler import DataHandler
from platform_components.EdgeLake_functions.blockchain_EL_functions import fetch_data_from_db
from keras import layers, optimizers, models
from tensorflow.python import keras
from ibmfl.model.model_update import ModelUpdate

from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import r2_score


logger = logging.getLogger(__name__)

# from logging import getLogger
# logger = getLogger(__name__)

# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from pipeline import run_pipeline


class WinniioDataHandler(DataHandler):
    def __init__(self, node_name, fl_model: keras.Model):
        """
        Initialize.

        Args:
            data_path: File path for the dataset
            batch_size (int): The batch size for the data loader
            **kwargs: Additional arguments, passed to super init and load_mnist_shard
        """
        super().__init__()

        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        # print("BEFORE LOAD DATASET")
        # (self.x_train, self.y_train), (self.x_test, self.y_test) = self.load_dataset(node_name, 1)
        # print("AFTER LOAD DATASET")
        self.fl_model = fl_model
        self.node_name = node_name



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
        query_train = f"sql {db_name} SELECT actuatorState, co2Value, eventCount, humidity, switchStatus, temperature, label FROM node_{node_name} WHERE round_number = {round_number} AND data_type = 'train'"
        query_test = f"sql {db_name} SELECT actuatorState, co2Value, eventCount, humidity, switchStatus, temperature, label FROM node_{node_name} WHERE round_number = {round_number} AND data_type = 'test'"

        try:
            train_data = fetch_data_from_db(self.edgelake_node_url, query_train)
            test_data = fetch_data_from_db(self.edgelake_node_url, query_test)

            # Assuming the data is returned as dictionaries with keys 'x' and 'y'
            query_train_result = np.array(train_data["Query"])
            x_train_images = []
            y_train_labels = []
            for i in range(len(query_train_result)):
                y_train_label = query_train_result[i]['label']
                del query_train_result[i]['label']
                x_train_image_np_array = np.array(list(query_train_result[i].values()), dtype=np.float32)

                x_train_images.append(x_train_image_np_array)
                y_train_labels.append(y_train_label)

            y_train_label_final = np.array(y_train_labels, dtype=np.float32)

            query_test_result = np.array(test_data["Query"])
            x_test_images = []
            y_test_labels = []
            for i in range(len(query_test_result)):
                y_test_label = query_test_result[i]['label']
                del query_test_result[i]['label']
                x_test_image_np_array = np.array(list(query_test_result[i].values()), dtype=np.float32)

                x_test_images.append(x_test_image_np_array)
                y_test_labels.append(y_test_label)

            x_train_images_final = np.array(x_train_images, dtype=np.float32)
            x_test_images_final = np.array(x_test_images, dtype=np.float32)

            # print("Train data shape after loading and reshaping:", x_train_images_final.shape)

            y_test_label_final = np.array(y_test_labels, dtype=np.float32)
            # print("Test data shape after loading:", x_test_images_final.shape)

        except Exception as e:
            raise IOError(f"Error fetching datasets: {str(e)}")

        return (x_train_images_final, y_train_label_final), (x_test_images_final, y_test_label_final)


    def get_data(self):
        """
        Gets pre-process mnist training and testing data.

        :return: training data
        :rtype: `tuple`
        """
        print("Train data shape in get_data:", self.x_train.shape)
        print("Test data shape in get_data:", self.x_test.shape)
        return (self.x_train, self.y_train), (self.x_test, self.y_test)

    def get_weights(self):
        return self.fl_model.weights

    def update_model(self, weights):
        if isinstance(weights, ModelUpdate):
            weights = weights.get("weights")
        self.fl_model.set_weights(weights)

    def train(self, round_number):
        (x_train, y_train), (x_test, y_test) = self.load_dataset(
            node_name=self.node_name, round_number=round_number)

        early_stopping = keras.callbacks.EarlyStopping(
            monitor='loss',
            # patience=2,
            restore_best_weights=True,
            mode='min'
        )

        x_train2 = x_train.reshape(-1, 1, 6)

        # history = self.fl_model.fit(x=x_train.reshape(-1, 1, 6), y=y_train,
        #                          verbose=1,
        #                             batch_size=len(x_train))
        history = self.fl_model.fit(self.batch_generator(x_train2, y_train,32),
                                    callbacks=[early_stopping],
                                    steps_per_epoch=50,
                                    epochs=1,
                                 verbose=1)

        # print(f'History is {history.history}')
        return self.get_weights()

    def batch_generator(self, x_train, y_train, batch_size):
        size = len(x_train)  # Total number of samples
        while True:  # This makes the generator infinite (to be used with fit)
            for start in range(0, size, batch_size):
                end = min(start + batch_size, size)
                x_batch = x_train[start:end]
                y_batch = y_train[start:end]
                yield x_batch, y_batch  # Yield the batch of data


    def get_all_test_data(self, node_name):
        # 1. run sql to get all test data for x and y
        # 2. check if number returned equals number in db
        # 3. return test data
        db_name = os.getenv("PSQL_DB_NAME")
        # query_test = f"sql {db_name} SELECT image, label FROM node_{node_name} WHERE data_type = 'test'"
        query_test = f"sql {db_name} SELECT actuatorState, co2Value, eventCount, humidity, switchStatus, temperature, label FROM node_{node_name} WHERE data_type = 'test'"

        test_data = fetch_data_from_db(self.edgelake_node_url, query_test)

        # Assuming the data is returned as dictionaries with keys 'x' and 'y'
        query_test_result = np.array(test_data["Query"])
        x_test_images = []
        y_test_labels = []
        for i in range(len(query_test_result)):
            y_test_label = query_test_result[i]['label']
            del query_test_result[i]['label']
            x_test_image_np_array = np.array(list(query_test_result[i].values()), dtype=np.float32)

            x_test_images.append(x_test_image_np_array)
            y_test_labels.append(y_test_label)

        y_test_labels_final = np.array(y_test_labels, dtype=np.float32)

        x_test_images_final = np.array(x_test_images, dtype=np.float32).reshape(-1, 1, 6)

        return x_test_images_final, y_test_labels_final


    def run_inference(self):
        x_test_images, y_test_labels = self.get_all_test_data(self.node_name)

        # SAMPLE CODE FOR HOW TO RUN PREDICT AND GET NON VECTOR OUTPUT: https://github.com/IBM/federated-learning-lib/blob/main/notebooks/crypto_fhe_pytorch/pytorch_classifier_p0.ipynb
        # y_pred = np.array([])
        # for i_samples in range(sample_count):
        #     pred = party.fl_model.predict(
        #         torch.unsqueeze(torch.from_numpy(test_digits[i_samples]), 0))
        #     y_pred = np.append(y_pred, pred.argmax())
        # acc = accuracy_score(y_true, y_pred) * 100

        # y_pred = np.array([])
        # sample_count = x_test_images.shape[0]  # number of test samples

        predictions = self.fl_model.predict_on_batch(x_test_images)

        predictions = predictions.reshape(-1)

        i = 1
        res = {}
        for prediction, label in zip(predictions, y_test_labels):
            res[i] = f"{prediction} --> {label}"
            i += 1
            if len(res) == 10:
                break

        mae = mean_absolute_error(y_test_labels, predictions)
        print("Mean Absolute Error (MAE):", mae)
        mse = mean_squared_error(y_test_labels, predictions)
        print("Mean Squared Error (MSE):", mse)
        rmse = np.sqrt(mse)
        print("Root Mean Squared Error (RMSE):", rmse)
        r2 = r2_score(y_test_labels, predictions)
        print("R² Score:", r2)
        reg_accuracy = self.regression_accuracy(y_test_labels, predictions, threshold=0.1)
        print("Regression Accuracy (within 10%):", reg_accuracy)

        return {"results": str(res), "mae": mae, "mse": mse, "rmse": rmse, "r2": r2, "reg_accuracy": reg_accuracy}
        # return acc

    def regression_accuracy(self, y_true, y_pred, threshold=0.1):
        correct = np.abs(y_true - y_pred) / y_true < threshold
        return np.mean(correct)