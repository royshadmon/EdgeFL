from pickle import dumps, loads

class LocalModelUpdate:
    """
    Class to store and manage local model updates using serialization.

    This class allows storing model weight updates using key-value pairs,
    where values are serialized using `pickle.dumps` for later retrieval.
    """
    def __init__(self, **weights):
        """
        Initialize instance with weights.

        :param weights: Key-value pairs representing model weight updates.
        """
        self.__model_updates = {}
        for key, value in weights.items():
            self.add(key, value)

    def add(self, key, value):
        """
        Add a model update by serializing and storing it.

        :param key: Unique ID for the model update.
        :param value: The model weight to be stored.
        :raises Exception: If serialization fails.
        """
        try:
            self.__model_updates[key] = dumps(value)
        except Exception as e:
            raise Exception(f"Error updating model update: {str(e)}")

    def get(self, key):
        """
        Retrieve a model update by deserializing the stored value.

        :param key: Unique ID for the model update.
        :return: The deserialized model update value.
        :raises Exception: If the key does not exist in stored updates.
        """
        if key not in self.__model_updates:
            raise Exception(f"Key {key} not found in model updates")
        return loads(self.__model_updates[key])

    def exist_key(self, key):
        """
        Check if a given key exists in the stored model updates.

        :param key: Unique ID for the model update.
        :return: True if the key exists, False otherwise.
        """
        return key in self.__model_updates
