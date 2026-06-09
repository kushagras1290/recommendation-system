from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    control_model: str
    treatment_model: str
    allocation: float = Field(0.5, ge=0.1, le=0.9)


class VariantResult(BaseModel):
    name: str
    model: str
    users_assigned: int
    avg_precision_at_10: float
    avg_ndcg_at_10: float
    expected_lift_percent: float


class ExperimentResult(BaseModel):
    experiment_id: int
    name: str
    status: str
    allocation: float
    variants: list[VariantResult]
    winner: str | None
    confidence: float
    created_at: datetime


class ExperimentListResponse(BaseModel):
    experiments: list[ExperimentResult]
    total: int
