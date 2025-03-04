
import numpy as np

# Takes in a list of ModelUpdates and returns new weights
def FedAvg_aggregate(models : list):
    my_weights = [d.get('weights') for d in models]
    fed_max = [np.average(np.stack(layer_weights), axis=0) for layer_weights in zip(*my_weights)]
    return fed_max


