"""Pipeline module permissions re-export."""
from core.rbac import Permission


def can_manage(role: str) -> bool:
    from core.rbac import role_has

    return role_has(role, Permission.PIPELINE_MANAGE)


def can_read(role: str) -> bool:
    from core.rbac import role_has

    return role_has(role, Permission.PIPELINE_READ)
