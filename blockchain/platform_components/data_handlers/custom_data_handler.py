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
import torch

from ibmfl.data.data_handler import DataHandler
import requests
import json

from ibmfl.model.model_update import ModelUpdate
from ibmfl.model.pytorch_fl_model import PytorchFLModel
from sklearn.metrics import accuracy_score

from EdgeLake_functions.blockchain_EL_functions import fetch_data_from_db

logger = logging.getLogger(__name__)


class CustomMnistPytorchDataHandler(DataHandler):
    def __init__(self, node_name, fl_model:PytorchFLModel):
        super().__init__()
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        # load the datasets from SQL
        (self.x_train, self.y_train), (self.x_test, self.y_test) = self.load_dataset(node_name, 1)
        self.fl_model = fl_model
        self.node_name = node_name
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

        test_data = fetch_data_from_db(self.edgelake_node_url, query_test)

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

    def train(self, round_number):
        (x_train, y_train), (x_test, y_test) = self.load_dataset(
            node_name=self.node_name, round_number=round_number)

        self.fl_model.fit_model(train_data=(x_train,y_train))
        return self.get_weights()

    def update_model(self, weights):
        if not isinstance(weights, ModelUpdate):
            model_update = ModelUpdate(weights=weights)
        else:
            model_update = ModelUpdate(weights=np.array(weights.get("weights")))
        self.fl_model.update_model(model_update)


    # def update_model(self, weights):
    #     for p1, p2 in zip(self.fl_model.get_weights(), weights):
    #         p1.data = torch.from_numpy(p2)
    #         p1.data.requires_grad = True

    def get_model_update(self):
        return self.fl_model.get_model_update()

    def get_weights(self):
        return self.fl_model.get_weights(to_numpy=True)

    def run_inference(self):
        x_test_images, y_test_labels = self.get_all_test_data(self.node_name)

        # SAMPLE CODE FOR HOW TO RUN PREDICT AND GET NON VECTOR OUTPUT: https://github.com/IBM/federated-learning-lib/blob/main/notebooks/crypto_fhe_pytorch/pytorch_classifier_p0.ipynb
        # y_pred = np.array([])
        # for i_samples in range(sample_count):
        #     pred = party.fl_model.predict(
        #         torch.unsqueeze(torch.from_numpy(test_digits[i_samples]), 0))
        #     y_pred = np.append(y_pred, pred.argmax())
        # acc = accuracy_score(y_true, y_pred) * 100

        y_pred = np.array([])
        sample_count = x_test_images.shape[0]  # number of test samples

        for i_samples in range(sample_count):
            # Get prediction for a single test sample
            pred = self.fl_model.predict(
                torch.unsqueeze(torch.from_numpy(x_test_images[i_samples]), 0)
            )

            # Append the predicted class (argmax) to y_pred
            y_pred = np.append(y_pred, pred.argmax())

        acc = accuracy_score(y_test_labels, y_pred) * 100

        return acc
