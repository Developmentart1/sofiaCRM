"""Activities module permissions re-export."""
from core.rbac import Permission


def can_read(role: str) -> bool:
    from core.rbac import role_has

    return role_has(role, Permission.ACTIVITY_READ)


def can_create(role: str) -> bool:
    from core.rbac import role_has

    return role_has(role, Permission.ACTIVITY_CREATE)
