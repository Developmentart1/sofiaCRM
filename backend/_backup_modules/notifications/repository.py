"""Notifications repository."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import Notification


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, notif_id: str) -> Notification:
        org = current_org_id()
        stmt = select(Notification).where(
            Notification.id == notif_id, Notification.organization_id == org
        )
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"notification {notif_id} not found")
        return row

    def list_for_user(self, user_id: str, *, limit: int = 50) -> list[Notification]:
        org = current_org_id()
        stmt = (
            select(Notification)
            .where(
                Notification.organization_id == org,
                Notification.user_id == user_id,
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def unread_count(self, user_id: str) -> int:
        org = current_org_id()
        stmt = select(func.count(Notification.id)).where(
            Notification.organization_id == org,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        return int(self.db.execute(stmt).scalar_one() or 0)

    def create(self, **kwargs) -> Notification:
        org = current_org_id()
        n = Notification(organization_id=org, **kwargs)
        self.db.add(n)
        self.db.flush()
        return n

    def mark_read(self, n: Notification) -> None:
        n.is_read = True
        n.read_at = datetime.now(UTC)
        self.db.flush()
