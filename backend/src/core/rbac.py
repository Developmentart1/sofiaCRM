"""Granular Role-Based Access Control.

Roles: admin, director, gerente, asesor, operaciones.
Each role gets a fixed set of Permission codes. A user is granted exactly
one role per organization. The check is centralised so endpoints declare
which permission they need; the helper raises ForbiddenError if denied.
"""

from enum import StrEnum
from typing import Final

from .errors import ForbiddenError


class Role(StrEnum):
    ADMIN = "admin"
    DIRECTOR = "director"
    GERENTE = "gerente"
    ASESOR = "asesor"
    OPERACIONES = "operaciones"


class Permission(StrEnum):
    # Organizations
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_MANAGE_USERS = "org:manage_users"

    # Users
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Pipelines
    PIPELINE_READ = "pipeline:read"
    PIPELINE_CREATE = "pipeline:create"
    PIPELINE_UPDATE = "pipeline:update"
    PIPELINE_DELETE = "pipeline:delete"
    PIPELINE_MANAGE = "pipeline:manage"

    # Contacts
    CONTACT_READ = "contact:read"
    CONTACT_CREATE = "contact:create"
    CONTACT_UPDATE = "contact:update"
    CONTACT_MERGE = "contact:merge"
    CONTACT_DELETE = "contact:delete"

    # Opportunities
    OPPORTUNITY_READ = "opportunity:read"
    OPPORTUNITY_CREATE = "opportunity:create"
    OPPORTUNITY_UPDATE = "opportunity:update"
    OPPORTUNITY_CHANGE_STAGE = "opportunity:change_stage"
    OPPORTUNITY_ASSIGN = "opportunity:assign"
    OPPORTUNITY_CLOSE = "opportunity:close"
    OPPORTUNITY_DELETE = "opportunity:delete"

    # Activities
    ACTIVITY_READ = "activity:read"
    ACTIVITY_CREATE = "activity:create"
    ACTIVITY_UPDATE = "activity:update"
    ACTIVITY_DELETE = "activity:delete"

    # Tasks
    TASK_READ = "task:read"
    TASK_CREATE = "task:create"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"

    # Documents
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_DELETE = "document:delete"

    # Audit
    AUDIT_READ = "audit:read"

    # Automation
    AUTOMATION_READ = "automation:read"
    AUTOMATION_MANAGE = "automation:manage"

    # Dashboards
    DASHBOARD_READ = "dashboard:read"

    # Reports
    REPORT_READ = "report:read"


ROLE_PERMISSIONS: Final[dict[Role, frozenset[Permission]]] = {
    Role.ADMIN: frozenset(Permission),  # full access
    Role.DIRECTOR: frozenset(
        {
            Permission.ORG_READ,
            Permission.USER_READ,
            Permission.PIPELINE_READ,
            Permission.PIPELINE_CREATE,
            Permission.PIPELINE_UPDATE,
            Permission.PIPELINE_DELETE,
            Permission.PIPELINE_MANAGE,
            Permission.CONTACT_READ,
            Permission.CONTACT_CREATE,
            Permission.CONTACT_UPDATE,
            Permission.CONTACT_MERGE,
            Permission.CONTACT_DELETE,
            Permission.OPPORTUNITY_READ,
            Permission.OPPORTUNITY_CREATE,
            Permission.OPPORTUNITY_UPDATE,
            Permission.OPPORTUNITY_CHANGE_STAGE,
            Permission.OPPORTUNITY_ASSIGN,
            Permission.OPPORTUNITY_CLOSE,
            Permission.OPPORTUNITY_DELETE,
            Permission.ACTIVITY_READ,
            Permission.ACTIVITY_CREATE,
            Permission.ACTIVITY_UPDATE,
            Permission.ACTIVITY_DELETE,
            Permission.TASK_READ,
            Permission.TASK_CREATE,
            Permission.TASK_UPDATE,
            Permission.TASK_DELETE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPLOAD,
            Permission.DOCUMENT_DELETE,
            Permission.AUDIT_READ,
            Permission.AUTOMATION_READ,
            Permission.AUTOMATION_MANAGE,
            Permission.DASHBOARD_READ,
            Permission.REPORT_READ,
        }
    ),
    Role.GERENTE: frozenset(
        {
            Permission.ORG_READ,
            Permission.USER_READ,
            Permission.PIPELINE_READ,
            Permission.CONTACT_READ,
            Permission.CONTACT_CREATE,
            Permission.CONTACT_UPDATE,
            Permission.CONTACT_MERGE,
            Permission.OPPORTUNITY_READ,
            Permission.OPPORTUNITY_CREATE,
            Permission.OPPORTUNITY_UPDATE,
            Permission.OPPORTUNITY_CHANGE_STAGE,
            Permission.OPPORTUNITY_ASSIGN,
            Permission.OPPORTUNITY_CLOSE,
            Permission.ACTIVITY_READ,
            Permission.ACTIVITY_CREATE,
            Permission.ACTIVITY_UPDATE,
            Permission.TASK_READ,
            Permission.TASK_CREATE,
            Permission.TASK_UPDATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPLOAD,
            Permission.AUTOMATION_READ,
            Permission.DASHBOARD_READ,
            Permission.REPORT_READ,
        }
    ),
    Role.ASESOR: frozenset(
        {
            Permission.ORG_READ,
            Permission.PIPELINE_READ,
            Permission.CONTACT_READ,
            Permission.CONTACT_CREATE,
            Permission.CONTACT_UPDATE,
            Permission.OPPORTUNITY_READ,
            Permission.OPPORTUNITY_CREATE,
            Permission.OPPORTUNITY_UPDATE,
            Permission.OPPORTUNITY_CHANGE_STAGE,
            Permission.ACTIVITY_READ,
            Permission.ACTIVITY_CREATE,
            Permission.ACTIVITY_UPDATE,
            Permission.TASK_READ,
            Permission.TASK_CREATE,
            Permission.TASK_UPDATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPLOAD,
            Permission.DASHBOARD_READ,
            Permission.REPORT_READ,
        }
    ),
    Role.OPERACIONES: frozenset(
        {
            Permission.ORG_READ,
            Permission.PIPELINE_READ,
            Permission.CONTACT_READ,
            Permission.OPPORTUNITY_READ,
            Permission.ACTIVITY_READ,
            Permission.ACTIVITY_CREATE,
            Permission.TASK_READ,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPLOAD,
            Permission.DASHBOARD_READ,
            Permission.REPORT_READ,
        }
    ),
}


def role_has(role: str, permission: Permission) -> bool:
    """Return True iff the named role grants the permission."""
    try:
        r = Role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS[r]


def require_permission(role: str, permission: Permission) -> None:
    """Raise ForbiddenError unless role grants permission."""
    if not role_has(role, permission):
        raise ForbiddenError(
            f"role '{role}' lacks permission '{permission.value}'",
            details={"role": role, "permission": permission.value},
        )


__all__ = ["Role", "Permission", "role_has", "require_permission", "ROLE_PERMISSIONS"]
