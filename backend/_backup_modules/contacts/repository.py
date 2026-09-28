"""Contact & Company repository. Every read scoped by org_id and deleted_at IS NULL."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import Company, Contact


class ContactRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, contact_id: str) -> Contact:
        org = current_org_id()
        stmt = select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == org,
            Contact.deleted_at.is_(None),
        )
        c = self.db.execute(stmt).scalar_one_or_none()
        if c is None:
            raise NotFoundError(f"contact {contact_id} not found")
        return c

    def find_duplicates(
        self,
        *,
        email_normalized: str | None,
        phone_normalized: str | None,
        exclude_id: str | None = None,
    ) -> list[tuple[Contact, str, str]]:
        """Return (contact, match_field, match_value) tuples."""
        org = current_org_id()
        conds = []
        if email_normalized:
            conds.append(Contact.email_normalized == email_normalized)
        if phone_normalized:
            conds.append(Contact.phone_normalized == phone_normalized)
        if not conds:
            return []
        stmt = (
            select(Contact)
            .where(
                Contact.organization_id == org,
                Contact.deleted_at.is_(None),
                or_(*conds),
            )
        )
        if exclude_id:
            stmt = stmt.where(Contact.id != exclude_id)
        results: list[tuple[Contact, str, str]] = []
        for c in self.db.execute(stmt).scalars().all():
            if email_normalized and c.email_normalized == email_normalized:
                results.append((c, "email", c.email_normalized))
            elif phone_normalized and c.phone_normalized == phone_normalized:
                results.append((c, "phone", c.phone_normalized))
        return results

    def list_all(self) -> list[Contact]:
        org = current_org_id()
        stmt = (
            select(Contact)
            .where(Contact.organization_id == org, Contact.deleted_at.is_(None))
            .order_by(Contact.full_name.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        *,
        contact_type: str,
        full_name: str,
        email: str | None,
        email_normalized: str | None,
        phone: str | None,
        phone_normalized: str | None,
        job_title: str | None,
        source: str | None,
        notes: str | None,
        company_id: str | None,
        owner_user_id: str | None,
        score: float,
    ) -> Contact:
        org = current_org_id()
        c = Contact(
            organization_id=org,
            contact_type=contact_type,
            full_name=full_name,
            email=email,
            email_normalized=email_normalized,
            phone=phone,
            phone_normalized=phone_normalized,
            job_title=job_title,
            source=source,
            notes=notes,
            company_id=company_id,
            owner_user_id=owner_user_id,
            score=score,
        )
        self.db.add(c)
        self.db.flush()
        return c

    def update(
        self,
        c: Contact,
        *,
        full_name: str | None = None,
        email: str | None = None,
        email_normalized: str | None = None,
        phone: str | None = None,
        phone_normalized: str | None = None,
        job_title: str | None = None,
        source: str | None = None,
        notes: str | None = None,
        company_id: str | None = None,
        owner_user_id: str | None = None,
        score: float | None = None,
        is_active: bool | None = None,
    ) -> Contact:
        if full_name is not None:
            c.full_name = full_name
        if email is not None:
            c.email = email
        if email_normalized is not None:
            c.email_normalized = email_normalized
        if phone is not None:
            c.phone = phone
        if phone_normalized is not None:
            c.phone_normalized = phone_normalized
        if job_title is not None:
            c.job_title = job_title
        if source is not None:
            c.source = source
        if notes is not None:
            c.notes = notes
        if company_id is not None:
            c.company_id = company_id
        if owner_user_id is not None:
            c.owner_user_id = owner_user_id
        if score is not None:
            c.score = score
        if is_active is not None:
            c.is_active = is_active
        self.db.flush()
        return c

    def soft_delete(self, c: Contact) -> None:
        from datetime import UTC, datetime

        c.deleted_at = datetime.now(UTC)
        self.db.flush()


class CompanyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, company_id: str) -> Company:
        org = current_org_id()
        stmt = select(Company).where(
            Company.id == company_id,
            Company.organization_id == org,
            Company.deleted_at.is_(None),
        )
        c = self.db.execute(stmt).scalar_one_or_none()
        if c is None:
            raise NotFoundError(f"company {company_id} not found")
        return c

    def list_all(self) -> list[Company]:
        org = current_org_id()
        stmt = (
            select(Company)
            .where(Company.organization_id == org, Company.deleted_at.is_(None))
            .order_by(Company.name.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        *,
        name: str,
        name_normalized: str,
        tax_id: str | None,
        industry: str | None,
        website: str | None,
        size: str | None,
        notes: str | None,
        owner_user_id: str | None,
    ) -> Company:
        org = current_org_id()
        c = Company(
            organization_id=org,
            name=name,
            name_normalized=name_normalized,
            tax_id=tax_id,
            industry=industry,
            website=website,
            size=size,
            notes=notes,
            owner_user_id=owner_user_id,
        )
        self.db.add(c)
        self.db.flush()
        return c

    def update(
        self,
        c: Company,
        *,
        name: str | None = None,
        name_normalized: str | None = None,
        tax_id: str | None = None,
        industry: str | None = None,
        website: str | None = None,
        size: str | None = None,
        notes: str | None = None,
        owner_user_id: str | None = None,
        is_active: bool | None = None,
    ) -> Company:
        if name is not None:
            c.name = name
        if name_normalized is not None:
            c.name_normalized = name_normalized
        if tax_id is not None:
            c.tax_id = tax_id
        if industry is not None:
            c.industry = industry
        if website is not None:
            c.website = website
        if size is not None:
            c.size = size
        if notes is not None:
            c.notes = notes
        if owner_user_id is not None:
            c.owner_user_id = owner_user_id
        if is_active is not None:
            c.is_active = is_active
        self.db.flush()
        return c

    def soft_delete(self, c: Company) -> None:
        from datetime import UTC, datetime

        c.deleted_at = datetime.now(UTC)
        self.db.flush()
