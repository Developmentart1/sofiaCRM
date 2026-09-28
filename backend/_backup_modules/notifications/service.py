"""Notifications service."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from core.event_bus import SyncEventBus
from .repository import NotificationRepository
from .schemas import NotificationCreate, NotificationRead


class NotificationService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = NotificationRepository(db)

    def list_for_user(self, user_id: str) -> list[NotificationRead]:
        rows = self.repo.list_for_user(user_id)
        return [NotificationRead.model_validate(n) for n in rows]

    def create(self, payload: NotificationCreate) -> NotificationRead:
        n = self.repo.create(
            user_id=str(payload.user_id),
            title=payload.title,
            body=payload.body,
            category=payload.category,
            related_entity_type=payload.related_entity_type,
            related_entity_id=str(payload.related_entity_id) if payload.related_entity_id else None,
        )
        return NotificationRead.model_validate(n)

    def mark_read(self, notif_id: str) -> NotificationRead:
        n = self.repo.get(notif_id)
        self.repo.mark_read(n)
        return NotificationRead.model_validate(n)

    def unread_count(self, user_id: str) -> int:
        return self.repo.unread_count(user_id)
