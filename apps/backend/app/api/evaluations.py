from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db_dep
from app.ml.registry import get_registry
from app.schemas.common import SuccessResponse
from app.schemas.evaluations import EvaluationResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.get("/latest", response_model=SuccessResponse[EvaluationResponse])
def latest_evaluation(
    request: Request,
    db: Session = Depends(get_db_dep),
) -> SuccessResponse[EvaluationResponse]:
    registry = get_registry()
    svc = EvaluationService(db, registry)
    result = svc.compute_metrics()
    return SuccessResponse(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )
