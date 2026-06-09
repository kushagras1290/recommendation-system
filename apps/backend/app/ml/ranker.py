from __future__ import annotations

import os
import pickle
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)
MODEL_VERSION = "ranker_v1"

try:
    import lightgbm as lgb
    _HAS_LGB = True
except ImportError:
    _HAS_LGB = False
    logger.warning("lightgbm_not_available", fallback="linear_scorer")


def _build_features(
    user_interaction_count: int,
    user_segment_enc: int,
    item_popularity_score: float,
    item_cf_score: float,
    item_content_score: float,
    item_avg_rating: float,
    item_year: int,
    category_enc: int,
    user_seen_category_count: int,
) -> list[float]:
    return [
        float(user_interaction_count),
        float(user_segment_enc),
        float(item_popularity_score),
        float(item_cf_score),
        float(item_content_score),
        float(item_avg_rating),
        float(max(0, 2025 - item_year)),
        float(category_enc),
        float(user_seen_category_count),
        float(item_popularity_score * item_cf_score),
        float(item_cf_score * item_content_score),
    ]


FEATURE_NAMES = [
    "user_interaction_count",
    "user_segment_enc",
    "item_popularity_score",
    "item_cf_score",
    "item_content_score",
    "item_avg_rating",
    "item_age_years",
    "category_enc",
    "user_seen_category_count",
    "popularity_x_cf",
    "cf_x_content",
]

SEGMENT_ENC = {"new": 0, "casual": 1, "active": 2, "power": 3}
CATEGORY_NAMES = [
    "Action", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Fantasy", "Horror", "Romance", "Sci-Fi",
    "Thriller", "War", "Western",
]
CATEGORY_ENC = {cat: idx for idx, cat in enumerate(CATEGORY_NAMES)}


class LGBMRanker:
    """
    LightGBM ranking model (LambdaRank) that re-scores candidates.
    Falls back to a weighted linear combination if LightGBM is unavailable.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._linear_weights = np.array([0.0, 0.0, 0.15, 0.35, 0.20, 0.20, -0.05, 0.0, 0.05, 0.0, 0.0])
        self.version = MODEL_VERSION

    def fit(
        self,
        training_rows: list[dict],
    ) -> None:
        """
        training_rows: [{features: list[float], label: float, query_id: int}]
        label = 1 if positive interaction, 0 otherwise (or continuous weight).
        """
        if not training_rows:
            logger.warning("ranker_no_training_data")
            return

        X = np.array([r["features"] for r in training_rows], dtype=np.float32)
        y = np.array([r["label"] for r in training_rows], dtype=np.float32)
        groups = []
        qids = [r["query_id"] for r in training_rows]
        current_qid, count = qids[0], 0
        for qid in qids:
            if qid == current_qid:
                count += 1
            else:
                groups.append(count)
                current_qid, count = qid, 1
        groups.append(count)

        if _HAS_LGB and len(set(qids)) >= 5:
            ds = lgb.Dataset(X, label=y, group=groups, feature_name=FEATURE_NAMES)
            params = {
                "objective": "lambdarank",
                "metric": "ndcg",
                "ndcg_eval_at": [5, 10],
                "num_leaves": 31,
                "learning_rate": 0.05,
                "n_estimators": 200,
                "verbosity": -1,
            }
            self._model = lgb.train(params, ds, num_boost_round=200)
            logger.info("ranker_lgbm_trained", n_rows=len(training_rows))
        else:
            self._model = None
            logger.info("ranker_using_linear_weights", n_rows=len(training_rows))

    def score(self, feature_rows: list[list[float]]) -> np.ndarray:
        if not feature_rows:
            return np.array([])
        X = np.array(feature_rows, dtype=np.float32)
        if _HAS_LGB and self._model is not None:
            return self._model.predict(X)
        return X @ self._linear_weights

    def is_trained(self) -> bool:
        return True  # linear fallback is always ready

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self._model, "weights": self._linear_weights}, f)
        logger.info("ranker_saved", path=path)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)  # nosec
        self._model = data["model"]
        self._linear_weights = data["weights"]
        logger.info("ranker_loaded", path=path)
