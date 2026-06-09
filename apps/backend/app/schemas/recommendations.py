from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ModelType = Literal["auto", "popularity", "content_based", "collaborative_filtering", "ranker"]


class RecommendationItem(BaseModel):
    item_id: str
    title: str
    category: str
    score: float
    rank: int
    explanation: str
    model_version: str
    attributes: dict = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: list[RecommendationItem]
    model_used: str
    is_cold_start: bool
    served_at: datetime


class ItemResponse(BaseModel):
    id: int
    external_id: str
    title: str
    category: str
    attributes: dict
    status: str

    model_config = {"from_attributes": True}
