from __future__ import annotations

import os
import pickle
from typing import NamedTuple

import numpy as np
import structlog
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

logger = structlog.get_logger(__name__)
MODEL_VERSION = "cf_v1"

N_FACTORS = 50


class CFScore(NamedTuple):
    item_id: int
    external_id: str
    title: str
    category: str
    score: float
    attributes: dict


class CollaborativeFilteringModel:
    """
    Collaborative filtering via truncated SVD on the implicit user-item matrix.

    Rating matrix R (users × items) where R[u,i] = cumulative weighted event score.
    Decompose R ≈ U * Σ * V^T, then predict r̂[u,i] = U[u] · (Σ * V^T)[:, i].
    """

    def __init__(self, n_factors: int = N_FACTORS) -> None:
        self.n_factors = n_factors
        self._user_factors: np.ndarray | None = None
        self._item_factors: np.ndarray | None = None
        self._user_index: dict[int, int] = {}
        self._item_index: dict[int, int] = {}
        self._item_ids: list[int] = []
        self._item_meta: dict[int, dict] = {}
        self.version = MODEL_VERSION

    def fit(self, interactions: list[dict], items: list[dict]) -> None:
        """
        interactions: [{user_id, item_id, weight, timestamp}]
        items: [{id, external_id, title, category, attributes}]
        """
        user_ids = sorted({ev["user_id"] for ev in interactions})
        item_ids = sorted({it["id"] for it in items})
        self._user_index = {uid: idx for idx, uid in enumerate(user_ids)}
        self._item_index = {iid: idx for idx, iid in enumerate(item_ids)}
        self._item_ids = item_ids
        self._item_meta = {it["id"]: it for it in items}

        n_users, n_items = len(user_ids), len(item_ids)
        rows, cols, data = [], [], []
        agg: dict[tuple[int, int], float] = {}

        for ev in interactions:
            key = (ev["user_id"], ev["item_id"])
            agg[key] = agg.get(key, 0.0) + ev["weight"]

        for (uid, iid), w in agg.items():
            u_idx = self._user_index.get(uid)
            i_idx = self._item_index.get(iid)
            if u_idx is not None and i_idx is not None and w > 0:
                rows.append(u_idx)
                cols.append(i_idx)
                data.append(w)

        matrix = csr_matrix((data, (rows, cols)), shape=(n_users, n_items), dtype=np.float32)

        k = min(self.n_factors, n_users - 1, n_items - 1)
        U, sigma, Vt = svds(matrix.astype(np.float64), k=k)
        self._user_factors = U * sigma[np.newaxis, :]
        self._item_factors = Vt.T

        logger.info("cf_model_fitted", n_users=n_users, n_items=n_items, n_factors=k)

    def recommend(
        self,
        user_id: int,
        k: int = 10,
        exclude_item_ids: set[int] | None = None,
    ) -> list[CFScore]:
        assert self._user_factors is not None, "Model not trained"
        exclude = exclude_item_ids or set()

        u_idx = self._user_index.get(user_id)
        if u_idx is None:
            return []

        user_vec = self._user_factors[u_idx]
        scores = self._item_factors @ user_vec

        ranked = np.argsort(scores)[::-1]
        results = []
        for idx in ranked:
            item_id = self._item_ids[idx]
            if item_id in exclude:
                continue
            meta = self._item_meta[item_id]
            results.append(CFScore(
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

    def known_user(self, user_id: int) -> bool:
        return user_id in self._user_index

    def is_trained(self) -> bool:
        return self._user_factors is not None

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "user_factors": self._user_factors,
                "item_factors": self._item_factors,
                "user_index": self._user_index,
                "item_index": self._item_index,
                "item_ids": self._item_ids,
                "item_meta": self._item_meta,
            }, f)
        logger.info("cf_model_saved", path=path)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)  # nosec
        self._user_factors = data["user_factors"]
        self._item_factors = data["item_factors"]
        self._user_index = data["user_index"]
        self._item_index = data["item_index"]
        self._item_ids = data["item_ids"]
        self._item_meta = data["item_meta"]
        logger.info("cf_model_loaded", path=path)
