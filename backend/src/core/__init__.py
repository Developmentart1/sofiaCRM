"""Core package: configuration, database, security, RBAC, errors, tenant,
pagination and event bus. Every module under modules/ depends only on this
package plus the stdlib + third-party libraries.
"""
from .config import Settings, get_settings
from .database import Base, SessionLocal, engine, get_db, session_scope
from .errors import (
    ConflictError,
    CRMError,
    ForbiddenError,
    MissingRequiredFieldError,
    NotFoundError,
    OrganizationBoundaryError,
    StageTransitionError,
    UnauthorizedError,
    ValidationError,
)
from .event_bus import (
    BaseEvent,
    SyncEventBus,
    configure_bus,
    get_bus,
)
from .pagination import Page, PageParams, PaginatedResponse
from .rbac import Permission, Role, require_permission, role_has
from .security import (
    create_access_token,
    decode_access_token,
    hash_password,
    sign_storage_url,
    verify_password,
    verify_storage_url,
)
from .tenant import (
    current_org_id,
    current_org_id_or_none,
    current_user_id,
    current_user_id_or_none,
    org_scope,
    reset_org,
    reset_user_id,
    set_org,
    set_user_id,
)

__all__ = [
    "Settings",
    "get_settings",
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "session_scope",
    "BaseEvent",
    "SyncEventBus",
    "configure_bus",
    "get_bus",
    "Page",
    "PageParams",
    "PaginatedResponse",
    "Permission",
    "Role",
    "require_permission",
    "role_has",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "sign_storage_url",
    "verify_password",
    "verify_storage_url",
    "current_org_id",
    "current_org_id_or_none",
    "current_user_id",
    "current_user_id_or_none",
    "org_scope",
    "set_org",
    "reset_org",
    "set_user_id",
    "reset_user_id",
    "CRMError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "StageTransitionError",
    "MissingRequiredFieldError",
    "OrganizationBoundaryError",
]
