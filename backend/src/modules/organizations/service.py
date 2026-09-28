"""Organization service: bootstraps a tenant with its first admin user."""

from sqlalchemy.orm import Session

from core.errors import ValidationError
from core.rbac import Role
from core.security import hash_password
from modules.users.domain import User
from .domain import Organization
from .repository import OrganizationRepository
from .schemas import OrganizationCreate, OrganizationRead, OrganizationUpdate


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OrganizationRepository(db)

    def bootstrap(self, payload: OrganizationCreate) -> tuple[Organization, User]:
        """Create the tenant AND its first admin user in one transaction.

        This is the only place outside the auth module that creates a user.
        """
        org = self.repo.create(
            name=payload.name,
            slug=payload.slug,
            timezone=payload.timezone,
            currency=payload.currency,
            locale=payload.locale,
        )
        admin = User(
            organization_id=org.id,
            email=payload.admin_email.lower().strip(),
            email_normalized=payload.admin_email.lower().strip(),
            full_name=payload.admin_full_name.strip(),
            password_hash=hash_password(payload.admin_password),
            role=Role.ADMIN.value,
            is_active=True,
        )
        self.db.add(admin)
        self.db.flush()
        return org, admin

    def update(self, org_id: str, payload: OrganizationUpdate) -> OrganizationRead:
        org = self.repo.get(org_id)
        updated = self.repo.update(
            org,
            name=payload.name,
            timezone=payload.timezone,
            currency=payload.currency,
            locale=payload.locale,
            is_active=payload.is_active,
        )
        return OrganizationRead.model_validate(updated)

    def get(self, org_id: str) -> OrganizationRead:
        return OrganizationRead.model_validate(self.repo.get(org_id))

    def get_by_slug(self, slug: str) -> OrganizationRead:
        return OrganizationRead.model_validate(self.repo.get_by_slug(slug))

    def assert_active(self, org: Organization) -> None:
        if not org.is_active:
            raise ValidationError(f"organization {org.slug} is inactive")
