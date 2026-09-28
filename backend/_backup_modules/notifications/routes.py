"""Notifications routes (per-user inbox)."""
from __future__ import annotations

from fastapi import APIRouter, status

from core.audit import audit_log
from core.event_bus import get_bus
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
from .schemas import NotificationCreate, NotificationRead
from .service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _service(db):
    return NotificationService(db, get_bus())


@router.get("/me", response_model=list[NotificationRead])
def my_notifications(current: CurrentUserDep, db: DbSessionDep) -> list[NotificationRead]:
    # Note: filter is by the calling user's id (server-side trust — Bearer).
    return _service(db).list_for_user(current.id)


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
@audit_log("notification.create", entity_type="notification")
def create_notification(
    payload: NotificationCreate, current: CurrentUserDep, db: DbSessionDep
) -> NotificationRead:
    return _service(db).create(payload)


@router.post("/{notif_id}/read", response_model=NotificationRead)
@audit_log("notification.read", entity_type="notification")
def mark_read(
    notif_id: str, current: CurrentUserDep, db: DbSessionDep
) -> NotificationRead:
    return _service(db).mark_read(notif_id)
