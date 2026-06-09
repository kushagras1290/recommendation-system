from __future__ import annotations

from pydantic import BaseModel


class ModelMetrics(BaseModel):
    model_name: str
    precision_at_5: float
    precision_at_10: float
    recall_at_5: float
    recall_at_10: float
    ndcg_at_5: float
    ndcg_at_10: float
    mrr: float
    coverage: float
    diversity: float
    evaluated_users: int


class EvaluationResponse(BaseModel):
    models: list[ModelMetrics]
    train_size: int
    test_size: int
    total_items: int
    evaluated_at: str
