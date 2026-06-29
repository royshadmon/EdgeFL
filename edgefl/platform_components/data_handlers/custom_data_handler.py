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
from sklearn.utils.class_weight import compute_class_weight
import tensorflow as tf
from platform_components.lib.logger.logger_config import configure_logging
from platform_components.lib.modules.local_model_update import LocalModelUpdate
from platform_components.EdgeLake_functions.blockchain_EL_functions import fetch_data_from_db
from platform_components.model_fusion_algorithms.FedAvg import FedAvg_aggregate

from tensorflow.python.client import device_lib

device = "/GPU:0" if tf.config.list_physical_devices('GPU') else "/CPU:0"
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(device_lib.list_local_devices()) # debugging
    print(tf.sysconfig.get_build_info()) # debugging
    try:
        # Restrict Tensorflow to only use the first GPU
        tf.config.set_visible_devices(gpus[0], 'GPU')
        tf.config.experimental.set_memory_growth(gpus[0], True)
    except RuntimeError as e:
        print(e)

# node that system_query resides on
QUERY_NODE_URL=f"http://{os.getenv('EXTERNAL_IP')}"
# Edge Node containing data
EDGE_NODE_URL=os.getenv('EXTERNAL_TCP_IP_PORT', 'network')
# Logical database name
LOGICAL_DATABASE=os.getenv('LOGICAL_DATABASE')
# Table containing trained data
TRAIN_TABLE=os.getenv('TRAIN_TABLE')
# Table containing test data
TEST_TABLE=os.getenv('TEST_TABLE')


class MnistDataHandler():
    def __init__(self, node_name):
        # configure_logging(f"node_server_{port}")
        configure_logging("node_server_data_handler")
        self.logger = logging.getLogger(__name__)
        self.tcp_ip_port = os.getenv("EXTERNAL_TCP_IP_PORT")
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
        self.db_name = LOGICAL_DATABASE

        # Data Handler Initialization
        self.x_train = None
        self.y_train = None
        self.x_test = None
        self.y_test = None
        self.preprocessor = None
        self.testing_generator = None
        self.training_generator = None
        
        self.node_name = node_name

        self.fl_model = self.model_def()

        # load the datasets from SQL
        if self.node_name != 'agg': # for now, aggregator only allows for direct inference
            (self.x_train, self.y_train), (self.x_test, self.y_test) = self.load_dataset(node_name, 1)

            # pre-process the datasets
            self.preprocess()
            self.logger.debug(self.x_test)
            
    def model_def(self):
        # Model for MNIST classification
        model = models.Sequential([
            layers.Conv2D(32, kernel_size=(3, 3), activation="relu", input_shape=(28, 28, 1)),
            layers.MaxPooling2D(pool_size=(2, 2)),
            layers.Dropout(0.25),
            layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            layers.Dropout(0.25),
            layers.Flatten(),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.5),
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
        # load_dataset already reshapes and normalizes — only cast type here
        self.x_train = self.x_train.astype("float32")
        self.x_test  = self.x_test.astype("float32")

        self.logger.debug(f"Train data shape after preprocessing: {self.x_train.shape}")

        # Convert labels to correct type
        self.y_train = self.y_train.astype("int64")
        self.y_test = self.y_test.astype("int64")

    def run_inference(self):
        x_test_images, y_test_labels = self.get_all_test_data(self.node_name)

        # Get predictions
        with tf.device(device):
            predictions = self.fl_model.predict(x_test_images)
        y_pred = np.argmax(predictions, axis=1)

        # Calculate accuracy
        acc = accuracy_score(y_test_labels, y_pred) * 100

        return acc

    # TODO this function doesn't work
    def direct_inference(self, data):
        """
        Run inference on raw input data against given labels (already in MNIST format).
        Handles data conversion and validation internally.
        """
        data = np.array(data, dtype=np.float32)
        if data.max() > 1.0:
            data = data / 255.0
        res = self.fl_model.predict(data.reshape(1, 28, 28, 1))
        return np.argmax(res, axis=1)

        # Validate existence and check that there is the same number of data inputs as number of labels
        # if not data and not labels and len(data) != len(labels):
        #     raise ValueError(f"Data and labels lists must have the same length ({len(data)} != {len(labels)}).")

        # Validate labels/predictions and convert labels into a numpy array
        # if not isinstance(labels[0], int):
        #     raise TypeError(
        #         f"Labels must be a list of integers."
        #     )

        # Set up the test data properly
        test_images = []
        test_labels = []
        for image, label in zip(data, labels):
            # Convert data type to required numpy array
            image = np.array(image, dtype=np.float32)
            # Validate input dimensions and reshape
            if image.ndim not in [1, 3]:
                raise ValueError(
                    f"Invalid input dimensions ({image.ndim}D). "
                    "Expected 1D (784 elements) or 3D (28x28x1) array."
                )
            if image.size != 784:
                raise ValueError(
                    f"1D input must contain exactly 784 elements. Got {image.size}."
                )
            test_images.append(image)
            test_labels.append(label)

        # Convert test data into final numpy arrays
        img_rows, img_cols = 28, 28
        test_images_final = np.array(test_images, dtype=np.float32).reshape(-1, img_rows, img_cols, 1)
        # test_labels_final = np.array(test_labels, dtype=np.int64)

        # Get predictions
        with tf.device(device):
            predictions = self.fl_model.predict(test_images_final)
        y_pred = np.argmax(predictions, axis=1)

        # Calculate accuracy
        acc = accuracy_score(test_labels_final, y_pred) * 100

        return acc

    def train(self, round_number):
        (x_train, y_train), (x_test, y_test) = self.load_dataset(
            node_name=self.node_name, round_number=round_number)

        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=5,
            restore_best_weights=True,
            mode='max'
        )

        classes = np.unique(y_train)
        weights = compute_class_weight('balanced', classes=classes, y=y_train)
        class_weight_dict = dict(zip(classes, weights))

        with tf.device(device):
            self.fl_model.fit(
                x_train,
                y_train,
                batch_size=32,
                epochs=5,
                verbose=1,
                callbacks=[early_stopping],
                class_weight=class_weight_dict,
                validation_data=(x_test, y_test)
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
        query_test = f"sql {self.db_name} SELECT image, label FROM {TEST_TABLE} LIMIT 200"
        test_data = fetch_data_from_db(self.edgelake_node_url, query_test, self.tcp_ip_port)

        query_test_result = np.array(test_data["Query"])
        x_test_images = []
        y_test_labels = []
        for i in range(len(query_test_result)):
            x_test_image_np_array = np.array(ast.literal_eval(query_test_result[i]['image']))
            y_test_label = query_test_result[i]['label']
            x_test_images.append(x_test_image_np_array)
            y_test_labels.append(y_test_label)

        img_rows, img_cols = 28, 28
        x_test_images_final = np.array(x_test_images, dtype=np.float32).reshape(-1, img_rows, img_cols, 1) / 255.0
        y_test_labels_final = np.array(y_test_labels, dtype=np.int64)

        return x_test_images_final, y_test_labels_final

    # SAMPLE SQL Edgelake Commands:
    # FORMAT:
    # sql [dbms name] [query options] [sql command or select statement]
    # [dbms name] is the logical DBMS containing the data.
    # [query option] are formatting instructions and output directions (and are detailed below).
    # [SQL command] a SQL command including a SQL query.
    # EXAMPLE
    # sql lsl_demo "drop table lsl_demo"
    def load_dataset(self, node_name, round_number=None):

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

        # db_name = os.getenv("PSQL_DB_NAME")
        query_train = f"sql {self.db_name} SELECT image, label FROM {TRAIN_TABLE} LIMIT 1000"
        query_test = f"sql {self.db_name} SELECT image, label FROM {TEST_TABLE} LIMIT 200"

        try:
            train_data = fetch_data_from_db(self.edgelake_node_url, query_train, self.tcp_ip_port)
            test_data = fetch_data_from_db(self.edgelake_node_url, query_test, self.tcp_ip_port)

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
            x_train_images_final = np.array(x_train_images, dtype=np.float32).reshape(-1, img_rows, img_cols, 1) / 255.0
            x_test_images_final  = np.array(x_test_images,  dtype=np.float32).reshape(-1, img_rows, img_cols, 1) / 255.0

            self.logger.debug(f"Train data shape after loading and reshaping: {x_train_images_final.shape}")

            y_test_label_final = np.array(y_test_labels, dtype=np.int64)
            self.logger.debug(f"Test data shape after loading: {x_test_images_final.shape}")

        except Exception as e:
            raise IOError(f"Error fetching datasets: {str(e)}")

        return (x_train_images_final, y_train_label_final), (x_test_images_final, y_test_label_final)