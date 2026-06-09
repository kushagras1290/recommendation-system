from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db.database import get_db_dep
from app.db.models import Interaction, Item, User
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.events import EventCreate, EventListResponse, EventResponse
from app.services.event_service import EventService

router = APIRouter()


def _to_response(ev: Interaction, db: Session) -> EventResponse:
    user = db.query(User).filter(User.id == ev.user_id).first()
    item = db.query(Item).filter(Item.id == ev.item_id).first()
    return EventResponse(
        id=ev.id,
        user_external_id=user.external_id if user else str(ev.user_id),
        item_external_id=item.external_id if item else str(ev.item_id),
        event_type=ev.event_type,
        weight=ev.weight,
        timestamp=ev.timestamp,
    )


@router.post("", response_model=SuccessResponse[EventResponse], status_code=201)
def record_event(
    payload: EventCreate,
    request: Request,
    db: Session = Depends(get_db_dep),
) -> SuccessResponse[EventResponse]:
    svc = EventService(db)
    ev = svc.record_event(
        user_external_id=payload.user_external_id,
        item_external_id=payload.item_external_id,
        event_type=payload.event_type,
        timestamp=payload.timestamp,
        request_id=getattr(request.state, "request_id", None),
    )
    return SuccessResponse(
        data=_to_response(ev, db),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("", response_model=PaginatedResponse[EventResponse])
def list_events(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_dep),
) -> PaginatedResponse[EventResponse]:
    svc = EventService(db)
    offset = (page - 1) * page_size
    events, total = svc.get_recent_events(limit=page_size, offset=offset)
    return PaginatedResponse(
        data=[_to_response(ev, db) for ev in events],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=-(-total // page_size),
        ),
        request_id=getattr(request.state, "request_id", None),
    )
