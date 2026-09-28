"""@audit_log decorator. Records a row in audit_logs for the wrapped endpoint.

Best-effort: an audit insert failure is logged but does NOT fail the
request. The audit table is the system of record for accountability; if
it can't be written, we keep going rather than blocking the user.
"""
from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from core.tenant import current_org_id_or_none
from .domain import AuditLog

log = logging.getLogger(__name__)


def audit_log(action: str, *, entity_type: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Lazy imports to avoid circular import at module load.
            from fastapi import Request

            from modules.users.auth_deps import CurrentUser

            request: Request | None = None
            current: CurrentUser | None = None
            db: Session | None = None

            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                if isinstance(arg, CurrentUser):
                    current = arg
            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                if isinstance(value, CurrentUser):
                    current = value
                if isinstance(value, Session):
                    db = value

            result = func(*args, **kwargs)

            if db is not None:
                try:
                    org_id = current_org_id_or_none()
                    actor = current.id if current is not None else None
                    entity_id: str | None = None
                    if isinstance(result, dict) and "id" in result:
                        entity_id = str(result["id"])
                    row = AuditLog(
                        id=str(uuid4()),
                        organization_id=org_id or "",
                        actor_user_id=actor,
                        action=action,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        request_ip=(request.client.host if request and request.client else None),
                        user_agent=(request.headers.get("user-agent") if request else None),
                    )
                    db.add(row)
                    db.flush()
                except Exception as exc:  # noqa: BLE001
                    log.warning("audit_log failed for %s: %r", action, exc)

            return result

        return wrapper

    return decorator
