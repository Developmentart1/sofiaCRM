"""Audit log read queries scoped by tenant."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_recent(self, *, limit: int = 100) -> list[AuditLog]:
        org_id = current_org_id()
        stmt = (
            select(AuditLog)
            .where(AuditLog.organization_id == org_id)
            .order_by(AuditLog.occurred_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get(self, log_id: str) -> AuditLog:
        org_id = current_org_id()
        stmt = select(AuditLog).where(
            AuditLog.id == log_id, AuditLog.organization_id == org_id
        )
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"audit log {log_id} not found")
        return row
