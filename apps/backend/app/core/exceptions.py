from __future__ import annotations


class RecSysError(Exception):
    """Base exception for all recommendation system errors."""


class NotFoundError(RecSysError):
    """Raised when a requested resource does not exist."""


class ValidationError(RecSysError):
    """Raised when input validation fails."""


class ModelNotTrainedError(RecSysError):
    """Raised when inference is requested before a model has been trained."""


class TrainingError(RecSysError):
    """Raised when model training fails."""


class ExperimentError(RecSysError):
    """Raised for A/B experiment configuration or assignment errors."""
