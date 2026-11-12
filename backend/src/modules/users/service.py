"""User service: business rules, password changes, login."""

from sqlalchemy.orm import Session

from core.errors import ConflictError, UnauthorizedError, ValidationError
from core.rbac import Role
from core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from modules.organizations.repository import OrganizationRepository
from .domain import User
from .repository import UserRepository
from .schemas import LoginRequest, LoginResponse, UserCreate, UserRead, UserUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = UserRepository(db)

    def list_users(self) -> list[UserRead]:
        return [UserRead.model_validate(u) for u in self.repo.list_all()]

    def create(self, payload: UserCreate) -> UserRead:
        normalized = payload.email.lower().strip()
        if self.repo.get_by_email(normalized) is not None:
            raise ConflictError(f"user with email {payload.email} already exists")
        # Validate role
        try:
            Role(payload.role)
        except ValueError as exc:
            raise ValidationError(f"unknown role {payload.role!r}") from exc
        user = self.repo.create(
            email=payload.email,
            email_normalized=normalized,
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
            phone=payload.phone,
        )
        return UserRead.model_validate(user)

    def update(self, user_id: str, payload: UserUpdate) -> UserRead:
        user = self.repo.get(user_id)
        if payload.role is not None:
            try:
                Role(payload.role)
            except ValueError as exc:
                raise ValidationError(f"unknown role {payload.role!r}") from exc
        self.repo.update(
            user,
            full_name=payload.full_name,
            role=payload.role,
            phone=payload.phone,
            is_active=payload.is_active,
        )
        return UserRead.model_validate(user)

    def change_password(self, user_id: str, *, current: str, new: str) -> None:
        user = self.repo.get(user_id)
        if not verify_password(current, user.password_hash):
            raise UnauthorizedError("current password is incorrect")
        self.repo.update(user, password_hash=hash_password(new))
        self.db.commit()

    def login(self, payload: LoginRequest) -> LoginResponse:
        """Cross-tenant login: look up org by slug, then user by email+password."""
        org_repo = OrganizationRepository(self.db)
        org = org_repo.get_by_slug(payload.organization_slug)
        if not org.is_active:
            raise UnauthorizedError("organization is inactive")
        user = (
            self.db.query(User)
            .filter(
                User.organization_id == org.id,
                User.email_normalized == payload.email.lower().strip(),
            )
            .one_or_none()
        )
        if user is None or not user.is_active:
            raise UnauthorizedError("invalid credentials")
        if not verify_password(payload.password, user.password_hash):
            raise UnauthorizedError("invalid credentials")
        self.repo.touch_login(user)
        token = create_access_token(
            subject=user.id,
            organization_id=user.organization_id,
            role=user.role,
        )
        return LoginResponse(access_token=token, user=UserRead.model_validate(user))

    def login_company(self, organization_slug: str, password: str) -> LoginResponse:
        """Login the organization's admin using company + password."""
        org = OrganizationRepository(self.db).get_by_slug(organization_slug)
        if not org.is_active:
            raise UnauthorizedError("organization is inactive")
        user = (
            self.db.query(User)
            .filter(User.organization_id == org.id, User.role == Role.ADMIN.value, User.is_active.is_(True))
            .order_by(User.created_at.asc())
            .first()
        )
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("invalid company credentials")
        self.repo.touch_login(user)
        token = create_access_token(subject=user.id, organization_id=user.organization_id, role=user.role)
        return LoginResponse(access_token=token, user=UserRead.model_validate(user))

    def get(self, user_id: str) -> UserRead:
        return UserRead.model_validate(self.repo.get(user_id))