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
import tensorflow as tf
from platform_components.lib.logger.logger_config import configure_logging
from platform_components.lib.modules.local_model_update import LocalModelUpdate
from platform_components.EdgeLake_functions.blockchain_EL_functions import fetch_data_from_db
from platform_components.model_fusion_algorithms.FedAvg import FedAvg_aggregate
from scipy.stats import multivariate_normal


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
        else:
            self.prior = self.fit_layerwise_gaussian_prior()
            
    def model_def(self):
        num_classes = 10
        input_shape = (28, 28, 1)
        model = models.Sequential([
            layers.Input(shape=input_shape),
            layers.Conv2D(32, 3, activation="relu"),
            layers.Conv2D(32, 3, activation="relu"),
            layers.MaxPooling2D(),
            layers.Dropout(0.25),

            layers.Conv2D(64, 3, activation="relu"),
            layers.Conv2D(64, 3, activation="relu"),
            layers.MaxPooling2D(),
            layers.Dropout(0.25),

            layers.Flatten(),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.5),
            layers.Dense(num_classes, activation="softmax"),
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

        # Get predictions
        with tf.device(device):
            predictions = self.fl_model.predict(x_test_images)
        y_pred = np.argmax(predictions, axis=1)

        # Calculate accuracy
        acc = accuracy_score(y_test_labels, y_pred) * 100

        return acc

    def direct_inference(self, data):
        """
        Run inference on raw input data against given labels (already in MNIST format).
        Handles data conversion and validation internally.
        """
        data = np.array(data)
        res = self.fl_model.predict(data.reshape(1, 28, 28, 1))
        return np.argmax(res, axis=1)

    def train(self, round_number):
        (x_train, y_train), (x_test, y_test) = self.load_dataset(
            node_name=self.node_name, round_number=round_number)

        early_stopping = keras.callbacks.EarlyStopping(
            monitor='loss',
            restore_best_weights=True,
            mode='min'
        )

        with tf.device(device):
            self.fl_model.fit(
                x_train,
                y_train,
                batch_size=128,
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
        flat_models = [self.flatten_weights(m.get("weights")) for m in weights]
        indices = self.select_most_similar(flat_models, f=1)
        similar_models = [weights[i] for i in indices]

        global_model_weights = self.aggregate_models_geometric_median(similar_models)

        return global_model_weights

    def get_all_test_data(self, node_name):
        batch_amount = 50

        row_count_query = f"sql {self.db_name} SELECT count(*) FROM {TEST_TABLE}"
        row_count = fetch_data_from_db(self.edgelake_node_url, row_count_query, self.tcp_ip_port)
        num_rows = row_count["Query"][0].get('count(*)')

        for offset in range(1):
            query_test = f"sql {self.db_name} SELECT image, label FROM {TEST_TABLE} LIMIT 50"
            test_data = fetch_data_from_db(self.edgelake_node_url, query_test, self.tcp_ip_port)

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

    def load_dataset(self, node_name, round_number):
        """
        Loads the training and testing datasets by running SQL queries to fetch data.

        :param nb_points: Number of data points to fetch for training and testing datasets.
        :type nb_points: int
        :return: Training and testing datasets as NumPy arrays.
        :rtype: tuple
        """
        query_train = f"sql {self.db_name} SELECT image, label FROM {TRAIN_TABLE} WHERE round_number = {round_number}"
        query_test = f"sql {self.db_name} SELECT image, label FROM {TEST_TABLE} WHERE round_number = {round_number}"

        try:
            train_data = fetch_data_from_db(self.edgelake_node_url, query_train, self.tcp_ip_port)
            test_data = fetch_data_from_db(self.edgelake_node_url, query_test, self.tcp_ip_port)

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

    def select_most_similar(self, flat_models, f):
        """
        flat_models: list of 1D numpy arrays (one per model)
        f: number of outlier models to remove
        returns: indices of selected (n - f) models
        """
        flat_models = np.stack(flat_models)
        n = len(flat_models)

        diffs = flat_models[:, None, :] - flat_models[None, :, :]
        dists = np.linalg.norm(diffs, axis=2)

        scores = []
        k = n - f - 1

        for i in range(n):
            d = np.delete(dists[i], i)
            score = np.sum(np.sort(d)[:k])
            scores.append(score)

        selected = np.argsort(scores)[: n - f]
        return selected

    def flatten_weights(self, weights):
        """Flatten list of numpy arrays (layer weights) into a 1-D vector."""
        return np.concatenate([w.ravel() for w in weights])

    def geometric_median(self, points, eps=1e-5, max_iter=100):
        """
        points: list of numpy arrays with identical shape
        returns: geometric median array (same shape)
        """
        points = np.stack(points)
        guess = np.mean(points, axis=0)

        for _ in range(max_iter):
            diffs = points - guess
            distances = np.linalg.norm(diffs.reshape(points.shape[0], -1), axis=1)

            if np.any(distances == 0):
                return points[distances == 0][0]

            weights = 1.0 / distances
            weights /= weights.sum()

            new_guess = np.tensordot(weights, points, axes=1)

            if np.linalg.norm(new_guess - guess) < eps:
                return new_guess

            guess = new_guess

        return guess

    def aggregate_models_geometric_median(self, models):
        """
        models: list of Keras models
        returns: new Keras model with median-aggregated weights
        """
        all_weights = [m.get("weights") for m in models]

        num_layers = len(all_weights[0])
        aggregated_weights = []

        for layer_idx in range(num_layers):
            layer_params = [weights[layer_idx] for weights in all_weights]
            gm = self.geometric_median(layer_params)
            aggregated_weights.append(gm)

        return aggregated_weights

    def fit_layerwise_gaussian_prior(self):
        """
        Initialize Gaussian priors for each Conv2D layer.
        Returns a dictionary with multivariate Gaussian distributions.
        """
        model = self.model_def()
        layer_priors = {}

        for i, layer in enumerate(model.layers):
            if isinstance(layer, layers.Conv2D):
                kernel, bias = layer.get_weights()

                num_filters = kernel.shape[-1]
                weights_per_filter = kernel.shape[0] * kernel.shape[1] * kernel.shape[2]

                # Each filter gets its own multivariate Gaussian
                kernel_distributions = []
                for filter_idx in range(num_filters):
                    mean = np.zeros(weights_per_filter)
                    cov = np.eye(weights_per_filter) * (0.1 ** 2)
                    dist = multivariate_normal(mean=mean, cov=cov, allow_singular=True)
                    kernel_distributions.append(dist)

                layer_priors[f"{layer.name}_kernel"] = {
                    'distributions': kernel_distributions,
                    'kernel_shape': kernel.shape,
                    'weights_per_filter': weights_per_filter,
                    'num_filters': num_filters
                }

                # Bias prior (all biases together)
                bias_mean = np.zeros(num_filters)
                bias_cov = np.eye(num_filters) * (0.01 ** 2)

                layer_priors[f"{layer.name}_bias"] = {
                    'distribution': multivariate_normal(mean=bias_mean, cov=bias_cov),
                    'shape': bias.shape
                }

        return layer_priors

    def list_prior_layers(self, layer_priors):
        """
        List all layers in the priors dictionary.
        """
        print("\nAvailable layers in priors:")
        for key in layer_priors.keys():
            if '_kernel' in key:
                layer_name = key.replace('_kernel', '')
                num_filters = layer_priors[key]['num_filters']
                weights_per_filter = layer_priors[key]['weights_per_filter']
                print(f"  - {layer_name}: {num_filters} filters, {weights_per_filter} weights/filter")

    def deep_copy_priors(self, layer_priors):
        """
        Create a deep copy of layer priors (handles scipy distributions properly).
        """
        new_priors = {}

        for key, value in layer_priors.items():
            if '_kernel' in key:
                # Copy kernel distributions
                new_distributions = []
                for dist in value['distributions']:
                    # Recreate the distribution with copied parameters
                    new_dist = multivariate_normal(
                        mean=dist.mean.copy(),
                        cov=dist.cov.copy(),
                        allow_singular=True
                    )
                    new_distributions.append(new_dist)

                new_priors[key] = {
                    'distributions': new_distributions,
                    'kernel_shape': value['kernel_shape'],
                    'weights_per_filter': value['weights_per_filter'],
                    'num_filters': value['num_filters']
                }
            elif '_bias' in key:
                # Copy bias distribution
                old_dist = value['distribution']
                new_dist = multivariate_normal(
                    mean=old_dist.mean.copy(),
                    cov=old_dist.cov.copy(),
                    allow_singular=True
                )
                new_priors[key] = {
                    'distribution': new_dist,
                    'shape': value['shape']
                }

        return new_priors

    def conjugate_update_from_models(self, layer_priors, trained_models,
                                     likelihood_std=0.01):
        """
        Bayesian conjugate update using N trained models.
        Updates layer_priors to reflect information from trained models.

        Args:
            layer_priors: Dictionary from fit_layerwise_gaussian_prior()
            trained_models: List of trained Keras models
            likelihood_std: Uncertainty in each model's weights (smaller = more trust)

        Returns:
            Updated layer_priors dictionary
        """
        n_models = len(trained_models)

        if n_models == 0:
            print("Warning: No models provided for update")
            return layer_priors

        # Get the prior layer names (from the reference model)
        prior_conv_layers = [k.replace('_kernel', '') for k in layer_priors.keys() if '_kernel' in k]

        # Collect weights from all models, organized by layer INDEX not name
        layer_weights_by_index = {}

        for model in trained_models:
            # Get Conv2D layers from this model
            conv_layers = [layer for layer in model.layers if isinstance(layer, layers.Conv2D)]

            # Match by position in architecture
            for layer_idx, layer in enumerate(conv_layers):
                if layer_idx >= len(prior_conv_layers):
                    print(f"Warning: Model has more Conv2D layers than priors")
                    break

                kernel, bias = layer.get_weights()

                # Initialize storage using layer index
                if layer_idx not in layer_weights_by_index:
                    num_filters = kernel.shape[-1]
                    layer_weights_by_index[layer_idx] = {
                        'kernel': [[] for _ in range(num_filters)],
                        'bias': []
                    }

                # Collect kernel weights per filter
                for filter_idx in range(kernel.shape[-1]):
                    filter_w = kernel[:, :, :, filter_idx].flatten()
                    layer_weights_by_index[layer_idx]['kernel'][filter_idx].append(filter_w)

                # Collect bias weights
                layer_weights_by_index[layer_idx]['bias'].append(bias)

        # Update each layer's prior distributions by matching position
        for layer_idx, prior_layer_name in enumerate(prior_conv_layers):

            if layer_idx not in layer_weights_by_index:
                print(f"Warning: No weights found for layer {layer_idx} ({prior_layer_name}) in trained models")
                continue

            kernel_key = f"{prior_layer_name}_kernel"
            bias_key = f"{prior_layer_name}_bias"

            if kernel_key not in layer_priors:
                continue

            prior_info = layer_priors[kernel_key]
            num_filters = prior_info['num_filters']
            weights_per_filter = prior_info['weights_per_filter']

            collected_weights = layer_weights_by_index[layer_idx]

            # Update each filter's distribution
            for filter_idx in range(num_filters):
                observations = collected_weights['kernel'][filter_idx]

                if len(observations) == 0:
                    continue

                # Convert to array: (n_models, weights_per_filter)
                observations = np.array(observations)
                w_bar = np.mean(observations, axis=0)

                # Get current prior distribution
                prior_dist = prior_info['distributions'][filter_idx]
                mu_0 = prior_dist.mean
                Sigma_0 = prior_dist.cov

                # Extract diagonal variance
                sigma_0_sq = np.diag(Sigma_0)

                # Likelihood variance
                sigma_lik_sq = likelihood_std ** 2

                # Conjugate update for diagonal Gaussian
                precision_0 = 1 / sigma_0_sq
                precision_lik = 1 / sigma_lik_sq
                precision_1 = precision_0 + n_models * precision_lik
                variance_1 = 1 / precision_1

                # Posterior mean
                mu_1 = variance_1 * (precision_0 * mu_0 + n_models * precision_lik * w_bar)

                # Create new diagonal covariance matrix
                cov_1 = np.diag(variance_1)

                # Update the distribution
                prior_info['distributions'][filter_idx] = multivariate_normal(
                    mean=mu_1,
                    cov=cov_1,
                    allow_singular=True
                )

            # Update bias prior
            if bias_key in layer_priors:
                bias_observations = np.array(collected_weights['bias'])

                if len(bias_observations) > 0:
                    bias_bar = np.mean(bias_observations, axis=0)

                    # Get current bias prior
                    bias_prior = layer_priors[bias_key]['distribution']
                    mu_0_bias = bias_prior.mean
                    Sigma_0_bias = bias_prior.cov

                    # Extract diagonal variance
                    sigma_0_sq_bias = np.diag(Sigma_0_bias)

                    # Likelihood variance for bias
                    sigma_lik_sq_bias = (likelihood_std * 0.1) ** 2

                    # Conjugate update
                    precision_0_bias = 1 / sigma_0_sq_bias
                    precision_lik_bias = 1 / sigma_lik_sq_bias
                    precision_1_bias = precision_0_bias + n_models * precision_lik_bias
                    variance_1_bias = 1 / precision_1_bias

                    mu_1_bias = variance_1_bias * (precision_0_bias * mu_0_bias +
                                                   n_models * precision_lik_bias * bias_bar)

                    # Create new diagonal covariance
                    cov_1_bias = np.diag(variance_1_bias)

                    # Update the bias distribution
                    layer_priors[bias_key]['distribution'] = multivariate_normal(
                        mean=mu_1_bias,
                        cov=cov_1_bias,
                        allow_singular=True
                    )

        return layer_priors

    def compare_priors(self, old_priors, new_priors, layer_name=None, filter_idx=0):
        """
        Compare old and new priors to see how much they changed.

        Args:
            old_priors: Original priors
            new_priors: Updated priors
            layer_name: Layer name (e.g., 'conv2d', 'conv2d_1'). If None, uses first Conv2D layer
            filter_idx: Which filter to compare
        """
        # If no layer_name provided, get the first kernel layer
        if layer_name is None:
            kernel_keys = [k for k in old_priors.keys() if '_kernel' in k]
            if not kernel_keys:
                print("No kernel layers found in priors!")
                return
            kernel_key = kernel_keys[0]
            layer_name = kernel_key.replace('_kernel', '')
        else:
            kernel_key = f"{layer_name}_kernel"

        # Check if key exists
        if kernel_key not in old_priors:
            print(f"Layer '{kernel_key}' not found in old_priors!")
            print(f"Available layers: {[k for k in old_priors.keys() if '_kernel' in k]}")
            return

        if kernel_key not in new_priors:
            print(f"Layer '{kernel_key}' not found in new_priors!")
            print(f"Available layers: {[k for k in new_priors.keys() if '_kernel' in k]}")
            return

        # Check filter index
        num_filters = old_priors[kernel_key]['num_filters']
        if filter_idx >= num_filters:
            print(f"Filter index {filter_idx} out of range! Layer has {num_filters} filters.")
            return

        old_dist = old_priors[kernel_key]['distributions'][filter_idx]
        new_dist = new_priors[kernel_key]['distributions'][filter_idx]

        old_mean = old_dist.mean
        new_mean = new_dist.mean
        old_std = np.sqrt(np.diag(old_dist.cov))
        new_std = np.sqrt(np.diag(new_dist.cov))

        print(f"\n{layer_name} Filter {filter_idx} Changes:")
        print(f"Mean change (L2 norm): {np.linalg.norm(new_mean - old_mean):.6f}")
        print(f"Std change (L2 norm): {np.linalg.norm(new_std - old_std):.6f}")
        print(f"Mean reduction in std: {(1 - np.mean(new_std) / np.mean(old_std)) * 100:.2f}%")
        print(f"\nOld mean (first 5): {old_mean[:5]}")
        print(f"New mean (first 5): {new_mean[:5]}")
        print(f"\nOld std (first 5): {old_std[:5]}")
        print(f"New std (first 5): {new_std[:5]}")

    def sample_weights_from_prior(self, layer_priors):
        """
        Sample a complete set of weights from the updated prior.
        Returns a dictionary matching model layer structure.
        """
        sampled_weights = {}

        for kernel_key in layer_priors.keys():
            if '_kernel' not in kernel_key:
                continue

            prior_info = layer_priors[kernel_key]
            kernel_shape = prior_info['kernel_shape']
            num_filters = prior_info['num_filters']

            # Sample each filter
            filter_samples = []
            for filter_idx in range(num_filters):
                filter_weights = prior_info['distributions'][filter_idx].rvs()
                filter_samples.append(filter_weights)

            # Stack and reshape to kernel shape
            kernel = np.stack(filter_samples, axis=-1).reshape(kernel_shape)
            sampled_weights[kernel_key] = kernel

            # Sample bias
            bias_key = kernel_key.replace('_kernel', '_bias')
            if bias_key in layer_priors:
                bias = layer_priors[bias_key]['distribution'].rvs()
                sampled_weights[bias_key] = bias

        return sampled_weights


# Testing the conjugate update
def main():
    print("=" * 60)
    print("Testing Bayesian Prior Update")
    print("=" * 60)

    # Step 1: Initialize handler and priors
    m = MnistDataHandler("agg")
    m.tcp_ip_port = "127.0.0.1:32148"
    m.edgelake_node_url = "http://127.0.0.1:32149"
    m.db_name = "customers"

    print("\nStep 1: Initializing priors...")
    old_priors = m.fit_layerwise_gaussian_prior()
    m.list_prior_layers(old_priors)

    # Step 2: Train multiple models
    print("\n" + "=" * 60)
    print("Step 2: Training models...")
    print("=" * 60)

    trained_models = []
    num_models = 4

    for i in range(num_models):
        print(f"\nTraining model {i + 1}/{num_models}...")
        model = m.model_def()
        m.fl_model = model

        # Train and get weights
        weights = m.train(i + 1)
        m.update_model(weights)

        # Store the trained Keras model (not just weights)
        trained_models.append(m.fl_model)
        print(f"✓ Model {i + 1} training complete")

    # Step 3: Update priors using all trained models
    print("\n" + "=" * 60)
    print("Step 3: Updating priors with trained models...")
    print("=" * 60)

    # IMPORTANT: Create a deep copy so we can compare before/after
    # Use custom deep_copy_priors to handle scipy distributions properly
    new_priors = m.deep_copy_priors(old_priors)

    new_priors = m.conjugate_update_from_models(
        new_priors,
        trained_models,
        likelihood_std=0.01
    )

    # Step 4: Verify the update
    print("\n" + "=" * 60)
    print("Step 4: Verification")
    print("=" * 60)

    print("\nPrior structure check:")
    for key in new_priors.keys():
        if '_kernel' in key:
            print(f"\n{key}:")
            print(f"  - Number of filters: {new_priors[key]['num_filters']}")
            print(f"  - Weights per filter: {new_priors[key]['weights_per_filter']}")
            print(f"  - First filter mean (first 5): {new_priors[key]['distributions'][0].mean[:5]}")
            print(f"  - First filter std (first 5): {np.sqrt(np.diag(new_priors[key]['distributions'][0].cov))[:5]}")
        elif '_bias' in key:
            print(f"\n{key}:")
            print(f"  - Bias mean (first 5): {new_priors[key]['distribution'].mean[:5]}")
            print(f"  - Bias std (first 5): {np.sqrt(np.diag(new_priors[key]['distribution'].cov))[:5]}")

    # Step 5: Compare priors
    print("\n" + "=" * 60)
    print("Step 5: Comparing old vs new priors")
    print("=" * 60)

    # Compare all layers
    for kernel_key in [k for k in old_priors.keys() if '_kernel' in k]:
        layer_name = kernel_key.replace('_kernel', '')
        m.compare_priors(old_priors, new_priors, layer_name=layer_name, filter_idx=0)

    # Step 6: Sample from updated prior
    print("\n" + "=" * 60)
    print("Step 6: Sampling from updated prior")
    print("=" * 60)

    sampled = m.sample_weights_from_prior(new_priors)
    for key, value in sampled.items():
        print(f"{key}: shape {value.shape}")

    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()