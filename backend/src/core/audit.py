"""@audit_log decorator — self-contained, no module imports to avoid circular chains."""

import functools
import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from core.tenant import current_org_id_or_none

log = logging.getLogger("audit")


def audit_log(
    action: str, *, entity_type: str | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wraps a FastAPI endpoint to persist an AuditLog row on success."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)

            # Extract db session and user from kwargs (FastAPI dependencies)
            db: Session | None = kwargs.get("db")
            current = kwargs.get("current")
            if db is None or current is None:
                # Try positional args (unlikely for FastAPI but defensive)
                from fastapi import Request

                for a in args:
                    if isinstance(a, Request):
                        db = getattr(a.state, "db", None)
                        current = getattr(a.state, "current_user", None)

            if db is None:
                return result

            try:
                org_id = current_org_id_or_none() or (getattr(current, "organization_id", None))
                entity_id: str | None = None

                if isinstance(result, dict):
                    entity_id = result.get("id")
                elif hasattr(result, "id"):
                    entity_id = getattr(result, "id")

                import sqlalchemy as sa
                from datetime import UTC, datetime
                from uuid import uuid4

                stmt = (
                    sa.text(
                        "INSERT INTO audit_logs (id, organization_id, user_id, action, entity_type, entity_id, created_at) "
                        "VALUES (:id, :org_id, :user_id, :action, :entity_type, :entity_id, :created_at)"
                    )
                    .bindparams(
                        id=str(uuid4()),
                        org_id=org_id,
                        user_id=getattr(current, "id", "system"),
                        action=action,
                        entity_type=entity_type or func.__name__,
                        entity_id=entity_id,
                        created_at=datetime.now(UTC),
                    )
                )
                db.execute(stmt)
                db.commit()
            except Exception:
                log.exception("audit_log: failed to write audit entry")

            return result

        return wrapper

    return decorator


__all__ = ["audit_log"]
