"""Audit log read-only routes (admins and directors)."""
from __future__ import annotations

from fastapi import APIRouter, Query

from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
from .repository import AuditRepository
from .schemas import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    current: CurrentUserDep,
    db: DbSessionDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLogRead]:
    require_permission(current.role, Permission.AUDIT_READ)
    rows = AuditRepository(db).list_recent(limit=limit)
    return [AuditLogRead.model_validate(r) for r in rows]
