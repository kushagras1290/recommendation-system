from __future__ import annotations

import math
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.db.models import Item, User
from app.ml.registry import ModelRegistry
from app.schemas.evaluations import EvaluationResponse, ModelMetrics
from app.services.event_service import EventService

logger = structlog.get_logger(__name__)


def _precision_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    hits = sum(1 for item in recommended[:k] if item in relevant)
    return hits / k if k > 0 else 0.0


def _recall_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    hits = sum(1 for item in recommended[:k] if item in relevant)
    return hits / len(relevant) if relevant else 0.0


def _ndcg_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    dcg = sum(
        1.0 / math.log2(i + 2) for i, item in enumerate(recommended[:k]) if item in relevant
    )
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal > 0 else 0.0


def _mrr(recommended: list[int], relevant: set[int]) -> float:
    for rank, item in enumerate(recommended, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def _time_split(interactions: list[dict], test_ratio: float = 0.2) -> tuple[list[dict], list[dict]]:
    sorted_evs = sorted(interactions, key=lambda e: e["timestamp"])
    split_idx = int(len(sorted_evs) * (1 - test_ratio))
    return sorted_evs[:split_idx], sorted_evs[split_idx:]


class EvaluationService:
    def __init__(self, db: Session, registry: ModelRegistry) -> None:
        self._db = db
        self._registry = registry
        self._event_svc = EventService(db)

    def compute_metrics(self) -> EvaluationResponse:
        interactions = self._event_svc.get_all_interactions_raw()
        items = self._db.query(Item).filter(Item.status == "active").all()
        users = self._db.query(User).all()

        items_meta = [
            {"id": it.id, "external_id": it.external_id, "title": it.title,
             "category": it.category, "attributes": it.attributes}
            for it in items
        ]
        item_ids_all = {it.id for it in items}

        train, test = _time_split(interactions)

        test_relevant: dict[int, set[int]] = {}
        for ev in test:
            if ev["weight"] > 0:
                test_relevant.setdefault(ev["user_id"], set()).add(ev["item_id"])

        train_by_user: dict[int, list[dict]] = {}
        for ev in train:
            train_by_user.setdefault(ev["user_id"], []).append(ev)

        eval_users = [u for u in users if u.id in test_relevant][:50]

        model_results = []
        models_to_eval: list[tuple[str, object]] = []

        if self._registry.popularity.is_trained():
            models_to_eval.append(("popularity", self._registry.popularity))
        if self._registry.cf.is_trained():
            models_to_eval.append(("collaborative_filtering", self._registry.cf))
        if self._registry.content.is_trained():
            models_to_eval.append(("content_based", self._registry.content))
        if self._registry.ranker.is_trained() and self._registry.cf.is_trained():
            models_to_eval.append(("ranker", None))

        for model_name, model_obj in models_to_eval:
            p5_list, p10_list, r5_list, r10_list, ndcg5_list, ndcg10_list, mrr_list = [], [], [], [], [], [], []
            all_recommended_sets: list[set[int]] = []

            for user in eval_users:
                relevant = test_relevant.get(user.id, set())
                if not relevant:
                    continue
                seen = {ev["item_id"] for ev in train_by_user.get(user.id, [])}

                recs: list[int] = []
                try:
                    if model_name == "popularity":
                        cands = model_obj.recommend(k=10, exclude_item_ids=seen)
                        recs = [c.item_id for c in cands]
                    elif model_name == "collaborative_filtering":
                        if model_obj.known_user(user.id):
                            cands = model_obj.recommend(user.id, k=10, exclude_item_ids=seen)
                            recs = [c.item_id for c in cands]
                    elif model_name == "content_based":
                        user_evs = train_by_user.get(user.id, [])
                        if user_evs:
                            cands = model_obj.recommend(user_evs, k=10, exclude_item_ids=seen)
                            recs = [c.item_id for c in cands]
                    elif model_name == "ranker":
                        pop_c = self._registry.popularity.recommend(k=20, exclude_item_ids=seen)
                        cf_c = (
                            self._registry.cf.recommend(user.id, k=20, exclude_item_ids=seen)
                            if self._registry.cf.known_user(user.id) else []
                        )
                        merged_ids = list(dict.fromkeys(
                            [c.item_id for c in cf_c] + [c.item_id for c in pop_c]
                        ))[:20]
                        recs = merged_ids[:10]
                except Exception:
                    pass

                if not recs:
                    continue

                p5_list.append(_precision_at_k(recs, relevant, 5))
                p10_list.append(_precision_at_k(recs, relevant, 10))
                r5_list.append(_recall_at_k(recs, relevant, 5))
                r10_list.append(_recall_at_k(recs, relevant, 10))
                ndcg5_list.append(_ndcg_at_k(recs, relevant, 5))
                ndcg10_list.append(_ndcg_at_k(recs, relevant, 10))
                mrr_list.append(_mrr(recs, relevant))
                all_recommended_sets.append(set(recs))

            def _avg(lst: list[float]) -> float:
                return round(sum(lst) / len(lst), 4) if lst else 0.0

            coverage = (
                len({iid for s in all_recommended_sets for iid in s}) / len(item_ids_all)
                if item_ids_all else 0.0
            )
            diversity = (
                1.0 - sum(
                    len(s1 & s2) / max(len(s1 | s2), 1)
                    for i, s1 in enumerate(all_recommended_sets)
                    for s2 in all_recommended_sets[i + 1: i + 6]
                ) / max(len(all_recommended_sets), 1)
                if all_recommended_sets else 0.0
            )

            model_results.append(ModelMetrics(
                model_name=model_name,
                precision_at_5=_avg(p5_list),
                precision_at_10=_avg(p10_list),
                recall_at_5=_avg(r5_list),
                recall_at_10=_avg(r10_list),
                ndcg_at_5=_avg(ndcg5_list),
                ndcg_at_10=_avg(ndcg10_list),
                mrr=_avg(mrr_list),
                coverage=round(coverage, 4),
                diversity=round(max(diversity, 0.0), 4),
                evaluated_users=len(p5_list),
            ))

        return EvaluationResponse(
            models=model_results,
            train_size=len(train),
            test_size=len(test),
            total_items=len(items),
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )
