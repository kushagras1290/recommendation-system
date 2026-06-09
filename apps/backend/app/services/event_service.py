from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models import Interaction, Item, User
from app.schemas.events import EVENT_WEIGHTS

logger = structlog.get_logger(__name__)


class EventService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _get_or_create_user(self, external_id: str) -> User:
        user = self._db.query(User).filter(User.external_id == external_id).first()
        if user is None:
            user = User(external_id=external_id, segment="new")
            self._db.add(user)
            self._db.flush()
        return user

    def record_event(
        self,
        user_external_id: str,
        item_external_id: str,
        event_type: str,
        timestamp: datetime | None = None,
        request_id: str | None = None,
    ) -> Interaction:
        if event_type not in EVENT_WEIGHTS:
            raise ValidationError(f"Unknown event_type: {event_type}")

        item = self._db.query(Item).filter(Item.external_id == item_external_id).first()
        if item is None:
            raise NotFoundError(f"Item not found: {item_external_id}")
        if item.status != "active":
            raise ValidationError(f"Item is not active: {item_external_id}")

        user = self._get_or_create_user(user_external_id)
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        interaction = Interaction(
            user_id=user.id,
            item_id=item.id,
            event_type=event_type,
            weight=EVENT_WEIGHTS[event_type],
            timestamp=ts,
            request_id=request_id,
        )
        self._db.add(interaction)
        self._db.flush()
        logger.info("event_recorded", user=user_external_id, item=item_external_id, ev_type=event_type)
        return interaction

    def get_recent_events(self, limit: int = 100, offset: int = 0) -> tuple[list[Interaction], int]:
        query = self._db.query(Interaction).order_by(Interaction.timestamp.desc())
        total = query.count()
        events = query.offset(offset).limit(limit).all()
        return events, total

    def get_user_interactions(self, user_id: int) -> list[dict]:
        rows = (
            self._db.query(Interaction)
            .filter(Interaction.user_id == user_id)
            .order_by(Interaction.timestamp.desc())
            .all()
        )
        return [
            {
                "user_id": r.user_id,
                "item_id": r.item_id,
                "event_type": r.event_type,
                "weight": r.weight,
                "timestamp": r.timestamp,
            }
            for r in rows
        ]

    def get_all_interactions_raw(self) -> list[dict]:
        rows = self._db.query(Interaction).all()
        return [
            {
                "user_id": r.user_id,
                "item_id": r.item_id,
                "event_type": r.event_type,
                "weight": r.weight,
                "timestamp": r.timestamp,
            }
            for r in rows
        ]
