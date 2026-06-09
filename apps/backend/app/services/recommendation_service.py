from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.db.models import Item, Recommendation, User
from app.ml.ranker import CATEGORY_ENC, SEGMENT_ENC, _build_features
from app.ml.registry import ModelRegistry
from app.schemas.recommendations import RecommendationItem, RecommendationResponse
from app.services.event_service import EventService

logger = structlog.get_logger(__name__)
settings = get_settings()


def _explanation(model_name: str, category: str, score: float) -> str:
    templates = {
        "popularity": f"Trending {category} — highly rated by many users",
        "content_based": f"Matches your taste in {category}",
        "collaborative_filtering": f"Users like you enjoyed this {category}",
        "ranker": f"Personalised pick in {category} (score {score:.2f})",
    }
    return templates.get(model_name, f"Recommended {category}")


class RecommendationService:
    def __init__(self, db: Session, registry: ModelRegistry) -> None:
        self._db = db
        self._registry = registry
        self._event_svc = EventService(db)

    def _resolve_user(self, user_external_id: str) -> User:
        user = self._db.query(User).filter(User.external_id == user_external_id).first()
        if user is None:
            raise NotFoundError(f"User not found: {user_external_id}")
        return user

    def get_recommendations(
        self,
        user_external_id: str,
        k: int = 10,
        model: str = "auto",
    ) -> RecommendationResponse:
        k = min(k, settings.max_recommendation_k)
        user = self._resolve_user(user_external_id)

        interactions = self._event_svc.get_user_interactions(user.id)
        seen_item_ids = {ev["item_id"] for ev in interactions}
        is_cold_start = len(interactions) < settings.cold_start_threshold

        all_items = self._db.query(Item).filter(Item.status == "active").all()
        items_meta = [
            {
                "id": it.id,
                "external_id": it.external_id,
                "title": it.title,
                "category": it.category,
                "attributes": it.attributes,
            }
            for it in all_items
        ]

        model_used = model
        candidates: list = []

        if is_cold_start or model == "popularity" or not self._registry.popularity.is_trained():
            candidates = self._registry.popularity.recommend(k=k * 2, exclude_item_ids=seen_item_ids)
            model_used = "popularity"

        elif model in ("auto", "ranker") and self._registry.cf.is_trained():
            pop_cands = self._registry.popularity.recommend(k=30, exclude_item_ids=seen_item_ids)
            cf_cands = []
            if self._registry.cf.known_user(user.id):
                cf_cands = self._registry.cf.recommend(user.id, k=30, exclude_item_ids=seen_item_ids)
            content_cands = []
            if self._registry.content.is_trained() and interactions:
                content_cands = self._registry.content.recommend(interactions, k=30, exclude_item_ids=seen_item_ids)

            # Merge candidates, deduplicate
            seen_cand_ids: set[int] = set()
            merged: list = []
            for cand in cf_cands + content_cands + pop_cands:
                if cand.item_id not in seen_cand_ids:
                    merged.append(cand)
                    seen_cand_ids.add(cand.item_id)

            if not merged:
                candidates = pop_cands
                model_used = "popularity"
            else:
                pop_scores = {c.item_id: c.score for c in pop_cands}
                cf_scores = {c.item_id: c.score for c in cf_cands}
                content_scores = {c.item_id: c.score for c in content_cands}
                pop_max = max(pop_scores.values(), default=1.0) or 1.0
                cf_max = max(cf_scores.values(), default=1.0) or 1.0
                content_max = max(content_scores.values(), default=1.0) or 1.0

                feature_rows, cand_refs = [], []
                n_interactions = len(interactions)
                user_segment = SEGMENT_ENC.get(user.segment, 1)
                category_counts = {}
                for ev in interactions:
                    item = next((it for it in items_meta if it["id"] == ev["item_id"]), None)
                    if item:
                        cat = item["category"]
                        category_counts[cat] = category_counts.get(cat, 0) + 1

                for cand in merged:
                    meta = next((it for it in items_meta if it["id"] == cand.item_id), {})
                    attrs = meta.get("attributes", {})
                    cat = meta.get("category", "")
                    feats = _build_features(
                        user_interaction_count=n_interactions,
                        user_segment_enc=user_segment,
                        item_popularity_score=pop_scores.get(cand.item_id, 0.0) / pop_max,
                        item_cf_score=cf_scores.get(cand.item_id, 0.0) / cf_max,
                        item_content_score=content_scores.get(cand.item_id, 0.0) / content_max,
                        item_avg_rating=attrs.get("rating", 7.0),
                        item_year=attrs.get("year", 2000),
                        category_enc=CATEGORY_ENC.get(cat, 0),
                        user_seen_category_count=category_counts.get(cat, 0),
                    )
                    feature_rows.append(feats)
                    cand_refs.append(cand)

                scores = self._registry.ranker.score(feature_rows)
                ranked = sorted(zip(scores, cand_refs), key=lambda x: x[0], reverse=True)
                candidates = [c for _, c in ranked[: k * 2]]
                model_used = "ranker"

        elif model == "collaborative_filtering" and self._registry.cf.is_trained():
            if self._registry.cf.known_user(user.id):
                candidates = self._registry.cf.recommend(user.id, k=k * 2, exclude_item_ids=seen_item_ids)
            else:
                candidates = self._registry.popularity.recommend(k=k * 2, exclude_item_ids=seen_item_ids)
            model_used = "collaborative_filtering"

        elif model == "content_based" and self._registry.content.is_trained() and interactions:
            candidates = self._registry.content.recommend(interactions, k=k * 2, exclude_item_ids=seen_item_ids)
            model_used = "content_based"

        else:
            candidates = self._registry.popularity.recommend(k=k * 2, exclude_item_ids=seen_item_ids)
            model_used = "popularity"

        # Diversity: ensure at most 3 items per category
        final: list = []
        category_counter: dict[str, int] = {}
        for cand in candidates:
            cat = cand.category
            if category_counter.get(cat, 0) < 3:
                final.append(cand)
                category_counter[cat] = category_counter.get(cat, 0) + 1
            if len(final) >= k:
                break

        if len(final) < k:
            for cand in candidates:
                if cand not in final:
                    final.append(cand)
                if len(final) >= k:
                    break

        served_at = datetime.now(timezone.utc)
        result_items = []
        for rank, cand in enumerate(final[:k], start=1):
            explanation = _explanation(model_used, cand.category, cand.score)
            meta = next((it for it in items_meta if it["id"] == cand.item_id), {})
            rec = Recommendation(
                user_id=user.id,
                item_id=cand.item_id,
                score=cand.score,
                rank=rank,
                model_version=model_used,
                explanation=explanation,
                impressed=True,
            )
            self._db.add(rec)
            result_items.append(RecommendationItem(
                item_id=cand.external_id,
                title=cand.title,
                category=cand.category,
                score=round(cand.score, 4),
                rank=rank,
                explanation=explanation,
                model_version=model_used,
                attributes=cand.attributes,
            ))

        self._db.flush()
        logger.info("recommendations_served", user=user_external_id, model=model_used, k=len(result_items))

        return RecommendationResponse(
            user_id=user_external_id,
            recommendations=result_items,
            model_used=model_used,
            is_cold_start=is_cold_start,
            served_at=served_at,
        )

    def get_all_users(self) -> list[dict]:
        users = self._db.query(User).order_by(User.external_id).all()
        return [{"id": u.id, "external_id": u.external_id, "segment": u.segment} for u in users]
