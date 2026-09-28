"""Organization repository. Every method runs inside a tenant context.
Note: organization table is the *root* of tenancy; cross-tenant lookups are
only allowed in two cases — login (by slug) and the initial bootstrap path.
All other callers must already be inside an org_scope.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import ConflictError, NotFoundError
from .domain import Organization


class OrganizationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, org_id: str) -> Organization:
        org = self.db.get(Organization, org_id)
        if org is None:
            raise NotFoundError(f"organization {org_id} not found")
        return org

    def get_by_slug(self, slug: str) -> Organization:
        stmt = select(Organization).where(Organization.slug == slug)
        org = self.db.execute(stmt).scalar_one_or_none()
        if org is None:
            raise NotFoundError(f"organization with slug {slug!r} not found")
        return org

    def create(self, *, name: str, slug: str, timezone: str, currency: str, locale: str) -> Organization:
        if self.db.execute(select(Organization).where(Organization.slug == slug)).scalar_one_or_none():
            raise ConflictError(f"organization slug {slug!r} already taken")
        org = Organization(
            name=name,
            slug=slug,
            timezone=timezone,
            currency=currency,
            locale=locale,
        )
        self.db.add(org)
        self.db.flush()
        return org

    def update(
        self,
        org: Organization,
        *,
        name: str | None = None,
        timezone: str | None = None,
        currency: str | None = None,
        locale: str | None = None,
        is_active: bool | None = None,
    ) -> Organization:
        if name is not None:
            org.name = name
        if timezone is not None:
            org.timezone = timezone
        if currency is not None:
            org.currency = currency
        if locale is not None:
            org.locale = locale
        if is_active is not None:
            org.is_active = is_active
        self.db.flush()
        return org
