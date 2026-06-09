from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models import Experiment, User
from app.schemas.experiments import ExperimentCreate, ExperimentListResponse, ExperimentResult, VariantResult

logger = structlog.get_logger(__name__)


def _deterministic_variant(user_id: str, experiment_name: str, allocation: float) -> str:
    """Assign user to a variant deterministically using a hash."""
    digest = hashlib.md5(f"{experiment_name}:{user_id}".encode()).hexdigest()  # nosec — not for crypto
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return "control" if bucket < allocation else "treatment"


def _simulate_ab_metrics(
    variant_name: str,
    model_name: str,
    n_users: int,
    rng: random.Random,
) -> tuple[float, float]:
    """Simulate realistic A/B metrics for demo purposes."""
    base_precision = {"popularity": 0.08, "collaborative_filtering": 0.12, "content_based": 0.10, "ranker": 0.15}
    base_ndcg = {"popularity": 0.12, "collaborative_filtering": 0.18, "content_based": 0.15, "ranker": 0.22}
    noise = rng.gauss(0, 0.01)
    prec = max(0.0, base_precision.get(model_name, 0.10) + noise)
    ndcg = max(0.0, base_ndcg.get(model_name, 0.15) + noise)
    return prec, ndcg


class ExperimentService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_experiment(self, payload: ExperimentCreate) -> Experiment:
        existing = self._db.query(Experiment).filter(Experiment.name == payload.name).first()
        if existing:
            raise ValidationError(f"Experiment '{payload.name}' already exists")
        exp = Experiment(
            name=payload.name,
            description=payload.description,
            variants_json=json.dumps({
                "control": {"model": payload.control_model, "weight": payload.allocation},
                "treatment": {"model": payload.treatment_model, "weight": 1 - payload.allocation},
            }),
            allocation=payload.allocation,
            status="running",
        )
        self._db.add(exp)
        self._db.flush()
        logger.info("experiment_created", name=payload.name)
        return exp

    def get_user_variant(self, user_external_id: str, experiment_name: str) -> str:
        exp = self._db.query(Experiment).filter(Experiment.name == experiment_name).first()
        if exp is None:
            raise NotFoundError(f"Experiment not found: {experiment_name}")
        if exp.status != "running":
            raise ValidationError(f"Experiment '{experiment_name}' is not running")
        return _deterministic_variant(user_external_id, experiment_name, exp.allocation)

    def list_experiments(self) -> ExperimentListResponse:
        experiments = self._db.query(Experiment).order_by(Experiment.created_at.desc()).all()
        users = self._db.query(User).all()
        n_users = len(users)
        results = []

        for exp in experiments:
            variants = exp.variants
            rng = random.Random(exp.id)
            variant_results = []
            winner: str | None = None
            best_metric = -1.0

            for vname, vconfig in variants.items():
                model = vconfig.get("model", "popularity")
                n_assigned = int(n_users * (vconfig.get("weight", 0.5)))
                prec, ndcg = _simulate_ab_metrics(vname, model, n_assigned, rng)
                lift = 0.0
                if vname == "treatment" and variant_results:
                    control_ndcg = variant_results[0].avg_ndcg_at_10
                    lift = ((ndcg - control_ndcg) / control_ndcg * 100) if control_ndcg > 0 else 0.0

                vr = VariantResult(
                    name=vname,
                    model=model,
                    users_assigned=max(n_assigned, 1),
                    avg_precision_at_10=round(prec, 4),
                    avg_ndcg_at_10=round(ndcg, 4),
                    expected_lift_percent=round(lift, 2),
                )
                variant_results.append(vr)
                if ndcg > best_metric:
                    best_metric = ndcg
                    winner = vname

            confidence = round(0.75 + rng.uniform(0, 0.20), 2) if exp.status == "running" else 0.95
            results.append(ExperimentResult(
                experiment_id=exp.id,
                name=exp.name,
                status=exp.status,
                allocation=exp.allocation,
                variants=variant_results,
                winner=winner if exp.status != "draft" else None,
                confidence=confidence,
                created_at=exp.created_at,
            ))

        return ExperimentListResponse(experiments=results, total=len(results))
