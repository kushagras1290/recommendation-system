from __future__ import annotations

import os
import pickle
from typing import NamedTuple

import numpy as np
import structlog
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

logger = structlog.get_logger(__name__)
MODEL_VERSION = "content_v1"


class ContentScore(NamedTuple):
    item_id: int
    external_id: str
    title: str
    category: str
    score: float
    attributes: dict


class ContentBasedModel:
    """
    Content-based recommender using TF-IDF on item text + category features.

    User profile = weighted average of interacted item vectors.
    Recommendations = top-K items by cosine similarity to user profile.
    """

    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._item_vectors: np.ndarray | None = None
        self._item_ids: list[int] = []
        self._item_meta: dict[int, dict] = {}
        self.version = MODEL_VERSION

    def fit(self, items: list[dict]) -> None:
        """items: list of {id, external_id, title, category, attributes}"""
        texts = []
        for item in items:
            attrs = item.get("attributes", {})
            genre = item.get("category", "")
            desc = attrs.get("description", "")
            year = str(attrs.get("year", ""))
            text = f"{genre} {genre} {item['title']} {desc} {year}"
            texts.append(text)

        self._vectorizer = TfidfVectorizer(
            max_features=2000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )
        matrix = self._vectorizer.fit_transform(texts)
        self._item_vectors = normalize(matrix.toarray(), norm="l2")
        self._item_ids = [it["id"] for it in items]
        self._item_meta = {it["id"]: it for it in items}
        logger.info("content_model_fitted", n_items=len(items))

    def _build_user_profile(
        self,
        interactions: list[dict],
    ) -> np.ndarray | None:
        """Weighted mean of interacted item vectors."""
        id_to_idx = {iid: idx for idx, iid in enumerate(self._item_ids)}
        vectors, weights = [], []
        for ev in interactions:
            idx = id_to_idx.get(ev["item_id"])
            if idx is not None and ev["weight"] > 0:
                vectors.append(self._item_vectors[idx])
                weights.append(ev["weight"])
        if not vectors:
            return None
        profile = np.average(vectors, axis=0, weights=weights)
        norm = np.linalg.norm(profile)
        return profile / norm if norm > 0 else profile

    def recommend(
        self,
        interactions: list[dict],
        k: int = 10,
        exclude_item_ids: set[int] | None = None,
    ) -> list[ContentScore]:
        assert self._item_vectors is not None, "Model not trained"
        exclude = exclude_item_ids or set()

        profile = self._build_user_profile(interactions)
        if profile is None:
            return []

        scores = cosine_similarity(profile.reshape(1, -1), self._item_vectors)[0]
        ranked = np.argsort(scores)[::-1]

        results = []
        for idx in ranked:
            item_id = self._item_ids[idx]
            if item_id in exclude:
                continue
            meta = self._item_meta[item_id]
            results.append(ContentScore(
                item_id=item_id,
                external_id=meta["external_id"],
                title=meta["title"],
                category=meta["category"],
                score=float(scores[idx]),
                attributes=meta.get("attributes", {}),
            ))
            if len(results) >= k:
                break
        return results

    def is_trained(self) -> bool:
        return self._item_vectors is not None

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "vectorizer": self._vectorizer,
                "item_vectors": self._item_vectors,
                "item_ids": self._item_ids,
                "item_meta": self._item_meta,
            }, f)
        logger.info("content_model_saved", path=path)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)  # nosec
        self._vectorizer = data["vectorizer"]
        self._item_vectors = data["item_vectors"]
        self._item_ids = data["item_ids"]
        self._item_meta = data["item_meta"]
        logger.info("content_model_loaded", path=path)
