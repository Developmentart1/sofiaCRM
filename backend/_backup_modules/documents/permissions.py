"""Documents module permissions."""
from core.rbac import Permission


def can_read(role: str) -> bool:
    from core.rbac import role_has

    return role_has(role, Permission.DOCUMENT_READ)


def can_upload(role: str) -> bool:
    from core.rbac import role_has

    return role_has(role, Permission.DOCUMENT_UPLOAD)
