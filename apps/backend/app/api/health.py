from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.database import check_db_health
from app.ml.registry import get_registry

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    database: str
    models: dict[str, bool]


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    db_ok = check_db_health()
    registry = get_registry()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unreachable",
        models=registry.status(),
    )


@router.get("/ready")
def readiness() -> dict[str, str]:
    return {"status": "ready"}
