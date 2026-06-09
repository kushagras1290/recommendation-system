from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EVENT_TYPES = Literal["view", "click", "watch", "rate_positive", "rate_negative", "wishlist"]
EVENT_WEIGHTS: dict[str, float] = {
    "view": 0.3,
    "click": 0.5,
    "watch": 1.0,
    "rate_positive": 1.5,
    "rate_negative": -0.5,
    "wishlist": 0.8,
}


class EventCreate(BaseModel):
    user_external_id: str = Field(..., min_length=1, max_length=64)
    item_external_id: str = Field(..., min_length=1, max_length=64)
    event_type: EVENT_TYPES
    timestamp: datetime | None = None

    @field_validator("user_external_id", "item_external_id")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class EventResponse(BaseModel):
    id: int
    user_external_id: str
    item_external_id: str
    event_type: str
    weight: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    events: list[EventResponse]
    total: int
