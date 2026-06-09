from __future__ import annotations

import json
from datetime import timezone

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import TrainingError
from app.db.models import Item, ModelArtifact, User
from app.ml.ranker import CATEGORY_ENC, SEGMENT_ENC, _build_features
from app.ml.registry import ModelRegistry
from app.services.event_service import EventService

logger = structlog.get_logger(__name__)


class TrainingService:
    def __init__(self, db: Session, registry: ModelRegistry) -> None:
        self._db = db
        self._registry = registry
        self._event_svc = EventService(db)

    def _get_items_meta(self) -> list[dict]:
        items = self._db.query(Item).filter(Item.status == "active").all()
        return [
            {
                "id": it.id,
                "external_id": it.external_id,
                "title": it.title,
                "category": it.category,
                "attributes": it.attributes,
            }
            for it in items
        ]

    def _get_users_meta(self) -> list[dict]:
        users = self._db.query(User).all()
        return [{"id": u.id, "external_id": u.external_id, "segment": u.segment} for u in users]

    def train_all(self) -> dict[str, str]:
        interactions = self._event_svc.get_all_interactions_raw()
        items = self._get_items_meta()
        users = self._get_users_meta()

        if not interactions:
            raise TrainingError("No interaction data available. Seed the database first.")
        if not items:
            raise TrainingError("No items found in the database.")

        results: dict[str, str] = {}

        try:
            self._registry.popularity.fit(interactions, items)
            results["popularity"] = "ok"
        except Exception as exc:
            logger.error("popularity_train_failed", error=str(exc))
            results["popularity"] = f"failed: {exc}"

        try:
            self._registry.content.fit(items)
            results["content_based"] = "ok"
        except Exception as exc:
            logger.error("content_train_failed", error=str(exc))
            results["content_based"] = f"failed: {exc}"

        try:
            self._registry.cf.fit(interactions, items)
            results["collaborative_filtering"] = "ok"
        except Exception as exc:
            logger.error("cf_train_failed", error=str(exc))
            results["collaborative_filtering"] = f"failed: {exc}"

        try:
            training_rows = self._build_ranker_training_data(interactions, items, users)
            self._registry.ranker.fit(training_rows)
            results["ranker"] = "ok"
        except Exception as exc:
            logger.error("ranker_train_failed", error=str(exc))
            results["ranker"] = f"failed: {exc}"

        self._registry.save_all()
        self._update_model_artifacts(results)
        logger.info("training_complete", results=results)
        return results

    def _build_ranker_training_data(
        self,
        interactions: list[dict],
        items: list[dict],
        users: list[dict],
    ) -> list[dict]:
        pop_recs = {}
        if self._registry.popularity.is_trained():
            for it in items:
                cands = self._registry.popularity.recommend(k=50)
                pop_recs = {c.item_id: c.score for c in cands}
                break

        pop_max = max(pop_recs.values(), default=1.0) or 1.0
        item_meta = {it["id"]: it for it in items}
        user_meta = {u["id"]: u for u in users}

        user_interactions: dict[int, list[dict]] = {}
        for ev in interactions:
            user_interactions.setdefault(ev["user_id"], []).append(ev)

        rows = []
        for user_id, evs in user_interactions.items():
            u = user_meta.get(user_id, {})
            n_interactions = len(evs)
            segment_enc = SEGMENT_ENC.get(u.get("segment", "casual"), 1)
            pos_items = {ev["item_id"] for ev in evs if ev["weight"] > 0}
            category_counts: dict[str, int] = {}
            for ev in evs:
                meta = item_meta.get(ev["item_id"], {})
                cat = meta.get("category", "")
                category_counts[cat] = category_counts.get(cat, 0) + 1

            for ev in evs:
                iid = ev["item_id"]
                meta = item_meta.get(iid, {})
                attrs = meta.get("attributes", {})
                cat = meta.get("category", "")
                feats = _build_features(
                    user_interaction_count=n_interactions,
                    user_segment_enc=segment_enc,
                    item_popularity_score=pop_recs.get(iid, 0.0) / pop_max,
                    item_cf_score=0.5,
                    item_content_score=0.5,
                    item_avg_rating=attrs.get("rating", 7.0),
                    item_year=attrs.get("year", 2000),
                    category_enc=CATEGORY_ENC.get(cat, 0),
                    user_seen_category_count=category_counts.get(cat, 0),
                )
                rows.append({"features": feats, "label": float(iid in pos_items), "query_id": user_id})

        return rows

    def _update_model_artifacts(self, results: dict[str, str]) -> None:
        from datetime import datetime
        now = datetime.now(timezone.utc)
        model_map = {
            "popularity": self._registry.popularity,
            "content_based": self._registry.content,
            "collaborative_filtering": self._registry.cf,
            "ranker": self._registry.ranker,
        }
        for name, model in model_map.items():
            if results.get(name) == "ok":
                from app.core.config import get_settings
                settings = get_settings()
                import os
                artifact = (
                    self._db.query(ModelArtifact)
                    .filter(ModelArtifact.model_name == name)
                    .first()
                )
                path = os.path.join(settings.model_dir, f"{name}.pkl")
                if artifact is None:
                    artifact = ModelArtifact(model_name=name, version=model.version, artifact_path=path)
                    self._db.add(artifact)
                else:
                    artifact.version = model.version
                    artifact.artifact_path = path
                    artifact.trained_at = now
                    artifact.is_active = True
        self._db.flush()
