"""Organization permissions. Only admins may manage; everyone may read their own."""
from core.rbac import Permission


def can_manage(role: str) -> bool:
    from core.rbac import role_has

    return role_has(role, Permission.ORG_UPDATE)


def can_read(role: str) -> bool:
    from core.rbac import role_has

    return role_has(role, Permission.ORG_READ)
