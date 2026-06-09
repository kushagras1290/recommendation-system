from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db_dep
from app.schemas.common import SuccessResponse
from app.schemas.experiments import ExperimentCreate, ExperimentListResponse, ExperimentResult
from app.services.experiment_service import ExperimentService

router = APIRouter()


@router.post("", response_model=SuccessResponse[ExperimentResult], status_code=201)
def create_experiment(
    payload: ExperimentCreate,
    request: Request,
    db: Session = Depends(get_db_dep),
) -> SuccessResponse[ExperimentResult]:
    svc = ExperimentService(db)
    exp = svc.create_experiment(payload)
    result = svc.list_experiments()
    created = next((e for e in result.experiments if e.experiment_id == exp.id), None)
    return SuccessResponse(
        data=created,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("", response_model=SuccessResponse[ExperimentListResponse])
def list_experiments(
    request: Request,
    db: Session = Depends(get_db_dep),
) -> SuccessResponse[ExperimentListResponse]:
    svc = ExperimentService(db)
    result = svc.list_experiments()
    return SuccessResponse(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/{experiment_name}/assignment/{user_id}", response_model=SuccessResponse[dict])
def get_assignment(
    experiment_name: str,
    user_id: str,
    request: Request,
    db: Session = Depends(get_db_dep),
) -> SuccessResponse[dict]:
    svc = ExperimentService(db)
    variant = svc.get_user_variant(user_id, experiment_name)
    return SuccessResponse(
        data={"user_id": user_id, "experiment": experiment_name, "variant": variant},
        request_id=getattr(request.state, "request_id", None),
    )
