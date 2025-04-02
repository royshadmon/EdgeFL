"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""

import ast
import logging
import os

import numpy as np
from tensorflow.python import keras
from keras import layers, optimizers, models
from sklearn.metrics import accuracy_score

from platform_components.lib.logger.logger_config import configure_logging
from platform_components.lib.modules.local_model_update import LocalModelUpdate
from platform_components.EdgeLake_functions.blockchain_EL_functions import fetch_data_from_db
from platform_components.model_fusion_algorithms.FedAvg import FedAvg_aggregate


class MnistDataHandler():
    def __init__(self, node_name):
        # configure_logging(f"node_server_{port}")
        configure_logging("node_server_data_handler")
        self.logger = logging.getLogger(__name__)
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'

        # Data Handler Initialization
        self.x_train = None
        self.y_train = None
        self.x_test = None
        self.y_test = None
        self.preprocessor = None
        self.testing_generator = None
        self.training_generator = None
        
        self.node_name = node_name
        
        # load the datasets from SQL
        if self.node_name != 'aggregator':
            (self.x_train, self.y_train), (self.x_test, self.y_test) = self.load_dataset(node_name, 1)
            self.fl_model = self.model_def()

            # pre-process the datasets
            self.preprocess()
            self.logger.debug(self.x_test)
            
    def model_def(self):
        # Model for MNIST classification
        model = models.Sequential([
            layers.Conv2D(32, kernel_size=(3, 3), activation="relu", input_shape=(28, 28, 1)), # Applies 2d convolution, extracting features from the input images
            layers.MaxPooling2D(pool_size=(2, 2)), # Reduces spatial dimensions
            layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            layers.Flatten(), # Converts 2d feature maps to 1d feature vector
            layers.Dense(128, activation="relu"), # Fully connecting layers
            layers.Dense(10, activation="softmax")
        ])

        # Compile the model with classification-appropriate loss and metrics
        model.compile(
            loss="sparse_categorical_crossentropy",
            optimizer=optimizers.Adam(learning_rate=0.001),
            metrics=["accuracy"]
        )
        
        return model

    def get_data(self):
        """
        Gets pre-process mnist training and testing data.

        :return: training data
        :rtype: `tuple`
        """
        self.logger.debug(f"Train data shape in get_data: {self.x_train.shape}")
        self.logger.debug(f"Test data shape in get_data: {self.x_test.shape}")
        return (self.x_train, self.y_train), (self.x_test, self.y_test)

    def get_model_update(self):
        return self.fl_model.get_model_update()

    def get_weights(self):
        return self.fl_model.get_weights()

    def preprocess(self):
        """
        Preprocesses the training and testing datasets.
        :return: None
        """
        self.logger.debug(f"Train data shape before preprocessing: {self.x_train.shape}")
        self.logger.debug(f"Test data shape before preprocessing: {self.x_test.shape}")
        img_rows, img_cols = 28, 28
        self.logger.debug(f"Train data shape before preprocessing: {self.x_train.shape}")

        # Reshape to keras format
        self.x_train = self.x_train.reshape(-1, img_rows, img_cols, 1)
        self.x_test = self.x_test.reshape(-1, img_rows, img_cols, 1)

        self.logger.debug(f"Train data shape after preprocessing: {self.x_train.shape}")

        # Convert labels to correct type
        self.y_train = self.y_train.astype("int64")
        self.y_test = self.y_test.astype("int64")

    def run_inference(self):
        x_test_images, y_test_labels = self.get_all_test_data(self.node_name)

        # SAMPLE CODE FOR HOW TO RUN PREDICT AND GET NON VECTOR OUTPUT: https://github.com/IBM/federated-learning-lib/blob/main/notebooks/crypto_fhe_pytorch/pytorch_classifier_p0.ipynb
        # y_pred = np.array([])
        # for i_samples in range(sample_count):
        #     pred = party.fl_model.predict(
        #         torch.unsqueeze(torch.from_numpy(test_digits[i_samples]), 0))
        #     y_pred = np.append(y_pred, pred.argmax())
        # acc = accuracy_score(y_true, y_pred) * 100

        # Get predictions
        predictions = self.fl_model.predict(x_test_images)
        y_pred = np.argmax(predictions, axis=1)

        # Calculate accuracy
        acc = accuracy_score(y_test_labels, y_pred) * 100

        return acc

    def train(self, round_number):
        (x_train, y_train), (x_test, y_test) = self.load_dataset(
            node_name=self.node_name, round_number=round_number)

        early_stopping = keras.callbacks.EarlyStopping(
            monitor='loss',
            # patience=2,
            restore_best_weights=True,
            mode='min'
        )

        self.fl_model.fit(
            x_train,
            y_train,
            batch_size=128, # can also be 32
            epochs=1,
            verbose=1,
            callbacks=[early_stopping]
        )

        return self.get_weights()

    def update_model(self, weights):
        if isinstance(weights, LocalModelUpdate):
            weights = weights.get("weights")
        self.fl_model.set_weights(weights)
      
    def aggregate_model_weights(self, weights):
        aggregated_params = FedAvg_aggregate(weights)
        return aggregated_params

    def get_all_test_data(self, node_name):
        # 1. run sql to get all test data for x and y
        # 2. check if number returned equals number in db
        # 3. return test data
        batch_amount = 50 # TODO: make this parameterized
        db_name = os.getenv("PSQL_DB_NAME")

        # Get number of rows
        row_count_query = f"sql {db_name} SELECT count(*) FROM node_{node_name} WHERE data_type = 'test'"
        row_count = fetch_data_from_db(self.edgelake_node_url, row_count_query)
        num_rows = row_count["Query"][0].get('count(*)')
        # fetch in offsets of 50
        for offset in range(0, num_rows, batch_amount):
            query_test = f"sql {db_name} SELECT image, label FROM node_{node_name} WHERE data_type = 'test' OFFSET {offset}"
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
            x_test_images_final = np.array(x_test_images, dtype=np.float32).reshape(-1, img_rows, img_cols, 1)

            return x_test_images_final, y_test_labels_final

    # SAMPLE SQL Edgelake Commands:
    # FORMAT:
    # sql [dbms name] [query options] [sql command or select statement]
    # [dbms name] is the logical DBMS containing the data.
    # [query option] are formatting instructions and output directions (and are detailed below).
    # [SQL command] a SQL command including a SQL query.
    # EXAMPLE
    # sql lsl_demo "drop table lsl_demo"
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
        # self.logger.debug(query_train)
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
            x_train_images_final = np.array(x_train_images, dtype=np.float32).reshape(-1, img_rows, img_cols, 1)
            x_test_images_final = np.array(x_test_images, dtype=np.float32).reshape(-1, img_rows, img_cols, 1)

            self.logger.debug(f"Train data shape after loading and reshaping: {x_train_images_final.shape}")

            y_test_label_final = np.array(y_test_labels, dtype=np.int64)
            self.logger.debug(f"Test data shape after loading: {x_test_images_final.shape}")

        except Exception as e:
            raise IOError(f"Error fetching datasets: {str(e)}")

        return (x_train_images_final, y_train_label_final), (x_test_images_final, y_test_label_final)
