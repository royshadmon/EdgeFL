import abc
import logging
import numpy as np
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAggregationModel(ABC):
    """Base class for federated learning aggregation models."""

    def __init__(self, hyperparams=None, fl_model=None):
        self.hyperparams = hyperparams or {}
        self.global_params = hyperparams.get("global", {}) if hyperparams else {}
        self.local_params = hyperparams.get("local", {}) if hyperparams else None
        self.fl_model = fl_model

        self.rounds = self.global_params.get("rounds", 1) or 1
        self.curr_round = 0

        if fl_model and fl_model.is_fitted():
            model_update = fl_model.get_model_update()
        else:
            model_update = None

        self.current_model_weights = model_update.get("weights") if model_update else None

    @abstractmethod
    def update_weights(self, model_updates):
        """Update weights based on received model updates"""
        raise NotImplementedError

    def get_current_metrics(self):
        """Returns current training metrics"""
        raise NotImplementedError
