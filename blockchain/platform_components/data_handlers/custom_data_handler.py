"""
Licensed Materials - Property of IBM
Restricted Materials of IBM
20221069
© Copyright IBM Corp. 2023 All Rights Reserved.
"""
import ast
import logging
import os

import numpy as np

from ibmfl.data.data_handler import DataHandler
import requests
import json

logger = logging.getLogger(__name__)


class CustomMnistPytorchDataHandler(DataHandler):
    def __init__(self, node_name):
        super().__init__()
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        # load the datasets from SQL
        (self.x_train, self.y_train), (self.x_test, self.y_test) = self.load_dataset(node_name, 1)

        # pre-process the datasets
        self.preprocess()
        print(self.x_test)

    def get_data(self):
        """
        Gets pre-process mnist training and testing data.

        :return: training data
        :rtype: `tuple`
        """
        print("Train data shape in get_data:", self.x_train.shape)
        print("Test data shape in get_data:", self.x_test.shape)
        return (self.x_train, self.y_train), (self.x_test, self.y_test)


    def fetch_data_from_db(self, query):
        """
        Fetch data from the database using an HTTP request with the provided SQL query.

        :param query: The SQL query to fetch the data.
        :type query: str
        :return: Parsed JSON response containing the fetched data.
        :rtype: dict
        """
        headers = {
            'User-Agent': 'AnyLog/1.23',
            'command': query,
        }

        try:
            # Send the GET request
            response = requests.get(self.edgelake_node_url, headers=headers)

            # Raise an HTTPError if the response code indicates failure
            response.raise_for_status()

            # Parse the response JSON
            return response.json()
        except requests.exceptions.RequestException as e:
            raise IOError(f"Failed to execute SQL query: {e}")
        except json.JSONDecodeError:
            raise ValueError("The response from the request is not valid JSON.")


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
        query_train = f"sql {db_name} SELECT image, label FROM node_{node_name} WHERE round_number = {round_number} AND data_type = 'train'"
        query_test = f"sql {db_name} SELECT image, label FROM node_{node_name} WHERE round_number = {round_number} AND data_type = 'test'"


        try:
            train_data = self.fetch_data_from_db(query_train)
            test_data = self.fetch_data_from_db(query_test)

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

        return (x_train_images_final,  y_train_label_final), (x_test_images_final, y_test_label_final)

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
        Preprocesses the training and testing datasets.
        :return: None
        """
        print("Train data shape before preprocessing:", self.x_train.shape)
        print("Test data shape before preprocessing:", self.x_test.shape)
        img_rows, img_cols = 28, 28
        print("Train data shape before preprocessing:", self.x_train.shape)
        
        # Force reshape to 4D format [batch_size, channels, height, width]
        self.x_train = self.x_train.reshape(-1, 1, img_rows, img_cols)
        self.x_test = self.x_test.reshape(-1, 1, img_rows, img_cols)
        
        print("Train data shape after preprocessing:", self.x_train.shape)
        
        # Convert labels to correct type
        self.y_train = self.y_train.astype("int64")
        self.y_test = self.y_test.astype("int64")

    def get_all_test_data(self, node_name):
        # 1. run sql to get all test data for x and y
        # 2. check if number returned equals number in db
        # 3. return test data
        db_name = os.getenv("PSQL_DB_NAME")
        query_test = f"sql {db_name} SELECT image, label FROM node_{node_name} WHERE data_type = 'test'"

        test_data = self.fetch_data_from_db(query_test)

        # Assuming the data is returned as dictionaries with keys 'x' and 'y'
        query_test_result = np.array(test_data["Query"])
        x_test_images = []
        y_test_labels = []
        for i in range(len(query_test_result)):
            x_test_image_np_array = np.array(ast.literal_eval(query_test_result[i]['image']))
            y_test_label = query_test_result[i]['label']
            x_test_images.append(x_test_image_np_array)
            y_test_labels.append(y_test_label)

        y_test_labels_final = np.array(y_test_labels, dtype=np.int64)

        img_rows, img_cols = 28, 28
        x_test_images_final = np.array(x_test_images, dtype=np.float32).reshape(-1, 1, img_rows, img_cols)

        return x_test_images_final, y_test_labels_final
