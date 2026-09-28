"""Multi-tenant context.

The current request's organization_id is held in a ContextVar so every
repository call can apply it without threading it through every signature.
This is the single substitute for PostgreSQL Row-Level Security: every
query MUST filter by current_org_id(). Any query that does not is a bug.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from .errors import OrganizationBoundaryError

_current_org_id: ContextVar[str | None] = ContextVar("current_org_id", default=None)
_current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def set_org(org_id: str | None) -> object:
    """Set the organisation id for the current logical request / script."""
    return _current_org_id.set(org_id)


def reset_org(token: object) -> None:
    """Restore the previous organisation id."""
    _current_org_id.reset(token)


def set_user_id(user_id: str | None) -> object:
    """Set the acting user id for the current logical request / script."""
    return _current_user_id.set(user_id)


def reset_user_id(token: object) -> None:
    """Restore the previous acting user id."""
    _current_user_id.reset(token)


def current_org_id() -> str:
    """Return the org id for the current context. Raises if not set."""
    value = _current_org_id.get()
    if value is None:
        raise OrganizationBoundaryError(
            "organization_id is not set in the current context",
            details={"hint": "wrap the call with org_scope() or call set_org()"},
        )
    return value


def current_org_id_or_none() -> str | None:
    """Return the org id or None if not set. Use in early bootstrap paths."""
    return _current_org_id.get()


def current_user_id() -> str:
    """Return the acting user id for the current context. Raises if not set."""
    value = _current_user_id.get()
    if value is None:
        raise OrganizationBoundaryError(
            "user_id is not set in the current context",
            details={"hint": "call set_user_id() or authenticate the request"},
        )
    return value


def current_user_id_or_none() -> str | None:
    """Return the acting user id or None if not set."""
    return _current_user_id.get()


@contextmanager
def org_scope(org_id: str) -> Iterator[None]:
    """Context manager that binds org_id for the duration of a block."""
    token = set_org(org_id)
    try:
        yield
    finally:
        reset_org(token)
