import os

"""
'0': Show all logs (default).
'1': Filter out INFO logs.
'2': Filter out WARNING logs.
'3': Filter out ERROR logs.
"""
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress warnings and info (only errors will be shown)

import tensorflow as tf
import numpy as np

# ✅ Check if GPU is available
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print("✅ GPU detected:", gpus[0])

    # Set memory growth to avoid allocating all memory upfront
    tf.config.experimental.set_memory_growth(gpus[0], True)

    # Force using GPU:0 by running operations inside the tf.device context
    with tf.device(f'/{gpus[0].name.split(":", 1)[-1]}'):  # (value: '/GPU:0') Corrected usage of the device name
        # x = tf.random.normal([10000, 20000])
        # print(x)

        # ✅ Load MNIST dataset
        (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
        x_train, x_test = x_train / 255.0, x_test / 255.0  # Normalize

        # ✅ Define a simple neural network
        model = tf.keras.models.Sequential([
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dense(10, activation='softmax')
        ])

        # ✅ Compile the model
        model.compile(optimizer='adam',
                      loss='sparse_categorical_crossentropy',
                      metrics=['accuracy'])

        """
        To resolve: 
            1. install python3.10 
            2. created venv310 
            3. added opencv-python-headless to requirements, as you need DNN 
            4. reran
            """
        # ✅ Train the model (will use GPU if available)
        model.fit(x_train, y_train, epochs=3, batch_size=128) # <-- this line causes stack script

        # ✅ Evaluate the model
        loss, accuracy = model.evaluate(x_test, y_test)
        print(f"Test Accuracy: {accuracy:.4f}")


else:
    print("❌ No GPU detected, running on CPU.")
