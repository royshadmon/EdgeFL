import logging
import numpy as np

from platform_components.lib.modules.aggregator_models.base_aggregation_model import BaseAggregationModel

logger = logging.getLogger(__name__)


class FedAvgAggregationModel(BaseAggregationModel):
    """
    Class for federated averaging aggregation models.
    """
    def __init__(self, hyperparams=None):
        super().__init__(hyperparams)
        self.name = "FedAvgAggregationModel"

    def update_weights(self, model_updates):
        """Averages the weights from all model updates"""
        if not model_updates:
            return None

        # Gets all the weights from each model into weights_list
        weights_list = []
        for update in model_updates:
            try:
                weights = np.array(update.get("weights"))
                weights_list.append(weights)
            except Exception:
                logger.warning("Failed to process model update")
                continue

        # This is where it calculates the mean of all the weights
        if weights_list:
            self.current_model_weights = np.mean(np.array(weights_list), axis=0).tolist()
            self.curr_round += 1

        return self.current_model_weights

    def get_current_metrics(self):
        """Returns current training metrics"""
        return {
            "rounds": self.rounds,
            "curr_round": self.curr_round
        }
