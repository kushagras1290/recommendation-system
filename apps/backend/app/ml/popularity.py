from __future__ import annotations

import os
import pickle
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, NamedTuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

MODEL_VERSION = "popularity_v1"
InteractionRecord = Mapping[str, Any]
ItemRecord = Mapping[str, Any]


class PopularityScore(NamedTuple):
    item_id: int
    external_id: str
    title: str
    category: str
    score: float
    attributes: dict[str, Any]


class PopularityModel:
    """
    Popularity-based recommender with exponential time decay.

    Score = sum(weight_i * decay(t_i)) for all interactions on an item.
    decay(t) = exp(-lambda * days_since_interaction)
    """

    def __init__(self, decay_lambda: float = 0.005) -> None:
        self.decay_lambda = decay_lambda
        self._scores: dict[int, float] = {}
        self._item_meta: dict[int, ItemRecord] = {}
        self._trained_at: datetime | None = None
        self.version = MODEL_VERSION

    def fit(self, interactions: Sequence[InteractionRecord], items: Sequence[ItemRecord]) -> None:
        """
        interactions: list of {item_id, weight, timestamp (datetime)}
        items: list of {id, external_id, title, category, attributes}
        """
        now = datetime.now(timezone.utc)
        scores: dict[int, float] = {}

        for event in interactions:
            item_id = int(event["item_id"])
            weight = float(event["weight"])
            ts = event["timestamp"]
            if not isinstance(ts, datetime):
                raise TypeError("Interaction timestamp must be a datetime")
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            days_ago = (now - ts).total_seconds() / 86400
            decay = np.exp(-self.decay_lambda * days_ago)
            scores[item_id] = scores.get(item_id, 0.0) + weight * decay

        self._scores = scores
        self._item_meta = {int(it["id"]): it for it in items}
        self._trained_at = now
        logger.info("popularity_model_fitted", n_items=len(scores))

    def recommend(self, k: int = 10, exclude_item_ids: set[int] | None = None) -> list[PopularityScore]:
        exclude = exclude_item_ids or set()
        sorted_items = sorted(
            [(iid, score) for iid, score in self._scores.items() if iid not in exclude],
            key=lambda x: x[1],
            reverse=True,
        )[:k]

        results = []
        for item_id, score in sorted_items:
            meta = self._item_meta.get(item_id, {})
            attributes = meta.get("attributes", {})
            results.append(PopularityScore(
                item_id=item_id,
                external_id=str(meta.get("external_id", str(item_id))),
                title=str(meta.get("title", "Unknown")),
                category=str(meta.get("category", "")),
                score=float(score),
                attributes=attributes if isinstance(attributes, dict) else {},
            ))
        return results

    def is_trained(self) -> bool:
        return bool(self._scores)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"scores": self._scores, "item_meta": self._item_meta, "trained_at": self._trained_at}, f)
        logger.info("popularity_model_saved", path=path)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)  # nosec: loading from trusted local path only
        self._scores = data["scores"]
        self._item_meta = data["item_meta"]
        self._trained_at = data["trained_at"]
        logger.info("popularity_model_loaded", path=path, n_items=len(self._scores))
