from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db_dep
from app.ml.registry import get_registry
from app.schemas.common import SuccessResponse
from app.services.training_service import TrainingService

router = APIRouter()


@router.post("/train", response_model=SuccessResponse[dict])
def trigger_training(
    request: Request,
    db: Session = Depends(get_db_dep),
) -> SuccessResponse[dict]:
    registry = get_registry()
    svc = TrainingService(db, registry)
    results = svc.train_all()
    return SuccessResponse(
        data={"status": "completed", "models": results},
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/status", response_model=SuccessResponse[dict])
def model_status(request: Request) -> SuccessResponse[dict]:
    registry = get_registry()
    return SuccessResponse(
        data=registry.status(),
        request_id=getattr(request.state, "request_id", None),
    )
