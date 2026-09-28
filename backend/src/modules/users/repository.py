"""User repository. Every read/write scoped by current organization."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: str) -> User:
        org_id = current_org_id()
        stmt = select(User).where(User.id == user_id, User.organization_id == org_id)
        user = self.db.execute(stmt).scalar_one_or_none()
        if user is None:
            raise NotFoundError(f"user {user_id} not found in this organization")
        return user

    def get_by_email(self, email_normalized: str) -> User | None:
        org_id = current_org_id()
        stmt = select(User).where(
            User.email_normalized == email_normalized,
            User.organization_id == org_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[User]:
        org_id = current_org_id()
        stmt = select(User).where(User.organization_id == org_id).order_by(User.full_name.asc())
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        *,
        email: str,
        email_normalized: str,
        full_name: str,
        password_hash: str,
        role: str,
        phone: str | None = None,
        is_active: bool = True,
    ) -> User:
        org_id = current_org_id()
        user = User(
            organization_id=org_id,
            email=email,
            email_normalized=email_normalized,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            phone=phone,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update(
        self,
        user: User,
        *,
        full_name: str | None = None,
        role: str | None = None,
        phone: str | None = None,
        is_active: bool | None = None,
        password_hash: str | None = None,
    ) -> User:
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if phone is not None:
            user.phone = phone
        if is_active is not None:
            user.is_active = is_active
        if password_hash is not None:
            user.password_hash = password_hash
        self.db.flush()
        return user

    def touch_login(self, user: User) -> None:
        from datetime import UTC, datetime

        user.last_login_at = datetime.now(UTC)
        self.db.flush()
