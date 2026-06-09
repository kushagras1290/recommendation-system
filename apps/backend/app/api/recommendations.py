from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db.database import get_db_dep
from app.ml.registry import get_registry
from app.schemas.common import SuccessResponse
from app.schemas.recommendations import ModelType, RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter()


@router.get("/{user_id}", response_model=SuccessResponse[RecommendationResponse])
def get_recommendations(
    user_id: str,
    request: Request,
    k: int = Query(10, ge=1, le=50),
    model: ModelType = Query("auto"),
    db: Session = Depends(get_db_dep),
) -> SuccessResponse[RecommendationResponse]:
    registry = get_registry()
    svc = RecommendationService(db, registry)
    result = svc.get_recommendations(user_external_id=user_id, k=k, model=model)
    return SuccessResponse(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("", response_model=SuccessResponse[dict])
def list_users(
    request: Request,
    db: Session = Depends(get_db_dep),
) -> SuccessResponse[dict]:
    registry = get_registry()
    svc = RecommendationService(db, registry)
    users = svc.get_all_users()
    return SuccessResponse(
        data={"users": users, "total": len(users)},
        request_id=getattr(request.state, "request_id", None),
    )
