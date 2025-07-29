"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""

# import ast
import os
import logging

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from keras.src.metrics.metrics_utils import confusion_matrix

# from sklearn.preprocessing import MinMaxScaler

from platform_components.EdgeLake_functions.blockchain_EL_functions import fetch_data_from_db
from keras import layers, optimizers, models
from tensorflow.python import keras

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping

from sklearn.metrics import mean_squared_error, accuracy_score
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import r2_score

from platform_components.lib.modules.local_model_update import LocalModelUpdate
from platform_components.model_fusion_algorithms.FedAvg import FedAvg_aggregate

from platform_components.lib.logger.logger_config import configure_logging
logger = logging.getLogger(__name__)



# load_dotenv("./../../env_files/chest_xrays_bbox/chest_xrays_bbox1.env") # change path if respective env is elsewhere

CLASSES = [
    "Infiltrate",
    "Atelectasis",
    "Pneumonia",
    "Cardiomegaly",
    "Effusion",
    "Pneumothorax",
    "Mass",
    "Nodule"
]

class ChestXraysBBoxDataHandler():
    def __init__(self, node_name, db_name):
        """
        Initialize.

        Args:
            data_path: File path for the dataset
            batch_size (int): The batch size for the data loader
            **kwargs: Additional arguments, passed to super init and load_mnist_shard
        """
        # configure_logging(f"node_server_{port}")
        configure_logging("node_server_data_handler")
        self.logger = logging.getLogger(__name__)
        self.edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'

        self.db_name = os.getenv("LOGICAL_DATABASE")
        self.db_table = os.getenv("TRAIN_TABLE")

        # Data Handler Initialization
        self.image_root_dir = os.path.join(os.getenv("GITHUB_DIR"), os.getenv("IMAGE_ROOT_DIR"))
        self.train_df = None
        self.test_df = None

        self.data_generator = None
        self.training_generator = None
        self.testing_generator = None

        self.preprocessor = None

        self.node_name = node_name
        self.fl_model = self.model_def()
        # self.initialize_model()

    def initialize_model(self):
        self.load_dataset(self.node_name, 1)
        self.fl_model = self.model_def()

    def model_def(self):
        # num_classes = len(self.training_generator.class_indices)

        model = Sequential([
            Conv2D(16, (3, 3), activation="relu", input_shape=(224, 224, 1)),
            MaxPooling2D((2, 2)),
            Conv2D(32, (3, 3), activation="relu"),
            MaxPooling2D((2, 2)),
            Conv2D(64, (3, 3), activation="relu"),
            MaxPooling2D((2, 2)),
            Flatten(),
            Dense(64, activation="relu"),
            Dropout(0.5),
            Dense(8, activation="softmax") # 7 unique labels
            # Dense(num_classes, activation="softmax")
        ])

        model.compile(
            optimizer="adam",
            loss="categorical_crossentropy",
            metrics=["accuracy"]
        )
        return model


    def load_dataset(self, node_name, round_number):

        """
        Loads the training and testing datasets by running SQL queries to fetch data.

        :param nb_points: Number of data points to fetch for training and testing datasets.
        :type nb_points: int
        """

        query_train = f"""sql {self.db_name} SELECT image, width, height, class, x_min, y_min, x_max, y_max FROM {self.db_table} WHERE round_number = {round_number}AND data_type = 'train'"""
        query_test = f"""sql {self.db_name} SELECT image, width, height, class, x_min, y_min, x_max, y_max FROM {self.db_table} WHERE round_number = {round_number} AND data_type = 'test'"""

        try:
            train_data = fetch_data_from_db(self.edgelake_node_url, query_train)
            test_data = fetch_data_from_db(self.edgelake_node_url, query_test)

            # Convert the data into dataframes suitable for the data generator
            train_df = pd.DataFrame(train_data["Query"], columns=["image", "width", "height", "class", "x_min", "y_min", "x_max", "y_max"])
            test_df = pd.DataFrame(test_data["Query"], columns=["image", "width", "height", "class", "x_min", "y_min", "x_max", "y_max"])

            # Add the full path of the image; currently, image is the filename
            train_df["file_path"] = train_df["image"].apply(lambda x: os.path.join(self.image_root_dir, x))
            test_df["file_path"] = test_df["image"].apply(lambda x: os.path.join(self.image_root_dir, x))

            self.train_df = train_df
            self.test_df = test_df
            self.set_generators(train_df, test_df, 32)

        except Exception as e:
            raise IOError(f"Error fetching datasets: {str(e)}")


    def get_data(self):
        """
        Gets pre-process chest xray bbox training and testing data.

        :return: training data
        :rtype: `tuple`
        """
        return self.train_df, self.test_df

    def get_weights(self):
        return self.fl_model.weights

    def update_model(self, weights):
        if isinstance(weights, LocalModelUpdate):
            weights = weights.get("weights")
        self.fl_model.set_weights(weights)

    def train(self, round_number):
        self.load_dataset(node_name=self.node_name, round_number=round_number)

        early_stopping = EarlyStopping(
            monitor="loss",
            patience=10,
            restore_best_weights=True
        )

        history = self.fl_model.fit(
            self.training_generator,
            callbacks=[early_stopping],
            steps_per_epoch=30,
            epochs=1,
            verbose=1
        )

        return self.get_weights()


    def set_generators(self, training_data, testing_data, batch_size):
        self.data_generator = ImageDataGenerator(
            rescale=1.0/255.0,
            rotation_range=15,
            width_shift_range=0.1,
            horizontal_flip=True
        )

        self.training_generator = self.data_generator.flow_from_dataframe(
            dataframe=training_data,
            directory=self.image_root_dir,
            x_col="file_path",
            y_col="class",
            target_size=(224, 224),
            color_mode="grayscale",
            batch_size=batch_size,
            class_mode="categorical",
            classes=CLASSES,
            verbose=0
        )

        self.testing_generator = self.data_generator.flow_from_dataframe(
            dataframe=testing_data,
            directory=self.image_root_dir,
            x_col="file_path",
            y_col="class",
            target_size=(224, 224),
            color_mode="grayscale",
            batch_size=batch_size,
            class_mode="categorical",
            classes=CLASSES,
            verbose=0
        )

    # def get_all_test_data(self, node_name):
    #     pass

    def aggregate_model_weights(self, weights):
        aggregated_params = FedAvg_aggregate(weights)
        return aggregated_params

    # TODO: bbox.direct_inference()
    def direct_inference(self, data):
        """
        Run inference on raw input data against given labels (already in respective format).
        Handles data conversion and validation internally.
        """
        pass

    def run_inference(self):
        y_true = self.testing_generator.classes
        y_pred = self.fl_model.predict(self.testing_generator)
        y_pred = np.argmax(y_pred, axis=1)

        acc = accuracy_score(y_true, y_pred) * 100
        # cm = confusion_matrix(y_true, y_pred, 9)
        # print(cm)

        return acc

    # TODO: bbox.regression_accuracy() (maybe)
    def regression_accuracy(self, y_true, y_pred, threshold=0.1):
        correct = np.abs(y_true - y_pred) / y_true < threshold
        return np.mean(correct)


    # TODO: bbox.validate_data() (maybe)
    @staticmethod
    def validate_data(values):
        """


        Parameters:

        Raises:

        Returns:
        """
        pass