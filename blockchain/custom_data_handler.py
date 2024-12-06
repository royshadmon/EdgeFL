"""
Licensed Materials - Property of IBM
Restricted Materials of IBM
20221069
© Copyright IBM Corp. 2023 All Rights Reserved.
"""
import logging
import os

import numpy as np

from ibmfl.data.data_handler import DataHandler
import requests
import json

logger = logging.getLogger(__name__)


class CustomMnistPytorchDataHandler(DataHandler):
    def __init__(self):
        super().__init__()

        # load the datasets from SQL
        (self.x_train, self.y_train), (self.x_test, self.y_test) = self.load_dataset()

        # pre-process the datasets
        self.preprocess()

    def get_data(self):
        """
        Gets pre-process mnist training and testing data.

        :return: training data
        :rtype: `tuple`
        """
        return (self.x_train, self.y_train), (self.x_test, self.y_test)

    def load_dataset(self, node_name, round_number):

        def fetch_data_from_db(query):
            """
            Fetch data from the database using an HTTP request with the provided SQL query.

            :param query: The SQL query to fetch the data.
            :type query: str
            :return: Parsed JSON response containing the fetched data.
            :rtype: dict
            """
            headers = {
                'User-Agent': 'AnyLog/1.23',
                'command': 'sql mnist_fl SELECT * FROM node1'
            }

            try:
                # Send the GET request
                external_ip = os.getenv("EXTERNAL_IP")
                url = f'http://{external_ip}:32049'
                response = requests.get(url, headers=headers)

                # Raise an HTTPError if the response code indicates failure
                response.raise_for_status()

                # Parse the response JSON
                return response.json()
            except requests.exceptions.RequestException as e:
                raise IOError(f"Failed to execute SQL query: {e}")
            except json.JSONDecodeError:
                raise ValueError("The response from the request is not valid JSON.")

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
        query_train = f"SELECT image, label FROM node_{node_name} WHERE round_number = {round_number} AND data_type = 'train'"
        query_test = f"SELECT image, label FROM node_{node_name} WHERE round_number = {round_number} AND data_type = 'test'"

        try:
            train_data = fetch_data_from_db(query_train)
            test_data = fetch_data_from_db(query_test)

            # Assuming the data is returned as dictionaries with keys 'x' and 'y'
            x_train = np.array(train_data["x"])
            y_train = np.array(train_data["y"])
            x_test = np.array(test_data["x"])
            y_test = np.array(test_data["y"])

        except Exception as e:
            raise IOError(f"Error fetching datasets: {str(e)}")

        return (x_train, y_train), (x_test, y_test)

        # SAMPLE SQL Edglake Commands:
        # FORMAT:
        # sql [dbms name] [query options] [sql command or select statement]
        # [dbms name] is the logical DBMS containing the data.
        # [query option] are formatting instructions and output directions (and are detailed below).
        # [SQL command] a SQL command including a SQL query.
        # EXAMPLE
        # sql lsl_demo "drop table lsl_demo"

    def preprocess(self):
        """
        Preprocesses the training and testing dataset, \
        e.g., reshape the images according to self.channels_first; \
        convert the labels to binary class matrices.

        :return: None
        """
        img_rows, img_cols = 28, 28
        self.x_train = self.x_train.astype("float32").reshape(self.x_train.shape[0], 1, img_rows, img_cols)
        self.x_test = self.x_test.astype("float32").reshape(self.x_test.shape[0], 1, img_rows, img_cols)
        # print(self.x_train.shape[0], 'train samples')
        # print(self.x_test.shape[0], 'test samples')

        self.y_train = self.y_train.astype("int64")
        self.y_test = self.y_test.astype("int64")
        # print('y_train shape:', self.y_train.shape)
        # print(self.y_train.shape[0], 'train samples')
        # print(self.y_test.shape[0], 'test samples')
