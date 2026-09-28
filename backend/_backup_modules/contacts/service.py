"""Contact & Company service: business rules, duplicate detection, merge."""
from __future__ import annotations

from sqlalchemy.orm import Session

from core.errors import ConflictError, NotFoundError, ValidationError
from core.event_bus import (
    CompanyCreated,
    CompanyUpdated,
    ContactCreated,
    ContactMerged,
    ContactUpdated,
    SyncEventBus,
)
from .domain import Company, Contact
from .normalize import normalize_email, normalize_name, normalize_phone
from .repository import CompanyRepository, ContactRepository
from .schemas import (
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
    ContactCreate,
    ContactMergeRequest,
    ContactRead,
    ContactUpdate,
    DuplicateCandidate,
)


class ContactService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = ContactRepository(db)

    def list_contacts(self) -> list[ContactRead]:
        return [ContactRead.model_validate(c) for c in self.repo.list_all()]

    def get(self, contact_id: str) -> ContactRead:
        return ContactRead.model_validate(self.repo.get(contact_id))

    def create(self, payload: ContactCreate) -> ContactRead:
        email = normalize_email(str(payload.email) if payload.email else None)
        phone = normalize_phone(payload.phone)
        contact = self.repo.create(
            contact_type=payload.contact_type,
            full_name=payload.full_name.strip(),
            email=str(payload.email) if payload.email else None,
            email_normalized=email,
            phone=payload.phone,
            phone_normalized=phone,
            job_title=payload.job_title,
            source=payload.source,
            notes=payload.notes,
            company_id=str(payload.company_id) if payload.company_id else None,
            owner_user_id=str(payload.owner_user_id) if payload.owner_user_id else None,
            score=payload.score,
        )
        self.bus.publish(
            ContactCreated(
                organization_id=contact.organization_id,  # type: ignore[arg-type]
                contact_id=contact.uuid,  # type: ignore[arg-type]
                full_name=contact.full_name,
                email_normalized=contact.email_normalized,
            ),
            db=self.db,
        )
        return ContactRead.model_validate(contact)

    def update(self, contact_id: str, payload: ContactUpdate) -> ContactRead:
        c = self.repo.get(contact_id)
        changed: list[str] = []
        if payload.email is not None:
            c.email = str(payload.email)
            c.email_normalized = normalize_email(str(payload.email))
            changed.append("email")
        if payload.phone is not None:
            c.phone = payload.phone
            c.phone_normalized = normalize_phone(payload.phone)
            changed.append("phone")
        if payload.full_name is not None:
            c.full_name = payload.full_name.strip()
            changed.append("full_name")
        if payload.job_title is not None:
            c.job_title = payload.job_title
            changed.append("job_title")
        if payload.source is not None:
            c.source = payload.source
            changed.append("source")
        if payload.notes is not None:
            c.notes = payload.notes
            changed.append("notes")
        if payload.company_id is not None:
            c.company_id = str(payload.company_id)
            changed.append("company_id")
        if payload.owner_user_id is not None:
            c.owner_user_id = str(payload.owner_user_id)
            changed.append("owner_user_id")
        if payload.score is not None:
            c.score = payload.score
            changed.append("score")
        if payload.is_active is not None:
            c.is_active = payload.is_active
            changed.append("is_active")
        self.db.flush()
        self.bus.publish(
            ContactUpdated(
                organization_id=c.organization_id,  # type: ignore[arg-type]
                contact_id=c.uuid,  # type: ignore[arg-type]
                changed_fields=changed,
            ),
            db=self.db,
        )
        return ContactRead.model_validate(c)

    def soft_delete(self, contact_id: str) -> None:
        c = self.repo.get(contact_id)
        self.repo.soft_delete(c)

    def find_duplicates(
        self, *, email: str | None, phone: str | None
    ) -> list[DuplicateCandidate]:
        e = normalize_email(email)
        p = normalize_phone(phone)
        results = self.repo.find_duplicates(email_normalized=e, phone_normalized=p)
        return [
            DuplicateCandidate(
                contact=ContactRead.model_validate(c),
                match_field=field,
                match_value=value,
            )
            for c, field, value in results
        ]

    def merge(self, payload: ContactMergeRequest) -> ContactRead:
        if payload.winner_id == payload.loser_id:
            raise ValidationError("winner and loser must be different contacts")
        winner = self.repo.get(str(payload.winner_id))
        loser = self.repo.get(str(payload.loser_id))
        # Inherit missing fields from loser
        if not winner.email and loser.email:
            winner.email = loser.email
            winner.email_normalized = loser.email_normalized
        if not winner.phone and loser.phone:
            winner.phone = loser.phone
            winner.phone_normalized = loser.phone_normalized
        if not winner.job_title and loser.job_title:
            winner.job_title = loser.job_title
        if not winner.company_id and loser.company_id:
            winner.company_id = loser.company_id
        if not winner.owner_user_id and loser.owner_user_id:
            winner.owner_user_id = loser.owner_user_id
        # Sum the score (rewards unification)
        winner.score = min(100.0, winner.score + loser.score)
        # Soft delete the loser
        self.repo.soft_delete(loser)
        self.db.flush()
        self.bus.publish(
            ContactMerged(
                organization_id=winner.organization_id,  # type: ignore[arg-type]
                winner_id=winner.uuid,  # type: ignore[arg-type]
                loser_id=loser.uuid,  # type: ignore[arg-type]
            ),
            db=self.db,
        )
        return ContactRead.model_validate(winner)


class CompanyService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = CompanyRepository(db)

    def list_companies(self) -> list[CompanyRead]:
        return [CompanyRead.model_validate(c) for c in self.repo.list_all()]

    def get(self, company_id: str) -> CompanyRead:
        return CompanyRead.model_validate(self.repo.get(company_id))

    def create(self, payload: CompanyCreate) -> CompanyRead:
        normalized = normalize_name(payload.name) or payload.name.lower()
        c = self.repo.create(
            name=payload.name.strip(),
            name_normalized=normalized,
            tax_id=payload.tax_id,
            industry=payload.industry,
            website=payload.website,
            size=payload.size,
            notes=payload.notes,
            owner_user_id=str(payload.owner_user_id) if payload.owner_user_id else None,
        )
        self.bus.publish(
            CompanyCreated(
                organization_id=c.organization_id,  # type: ignore[arg-type]
                company_id=c.uuid,  # type: ignore[arg-type]
                name=c.name,
            ),
            db=self.db,
        )
        return CompanyRead.model_validate(c)

    def update(self, company_id: str, payload: CompanyUpdate) -> CompanyRead:
        c = self.repo.get(company_id)
        if payload.name is not None:
            c.name = payload.name.strip()
            c.name_normalized = normalize_name(payload.name) or payload.name.lower()
        if payload.tax_id is not None:
            c.tax_id = payload.tax_id
        if payload.industry is not None:
            c.industry = payload.industry
        if payload.website is not None:
            c.website = payload.website
        if payload.size is not None:
            c.size = payload.size
        if payload.notes is not None:
            c.notes = payload.notes
        if payload.owner_user_id is not None:
            c.owner_user_id = str(payload.owner_user_id)
        if payload.is_active is not None:
            c.is_active = payload.is_active
        self.db.flush()
        self.bus.publish(
            CompanyUpdated(
                organization_id=c.organization_id,  # type: ignore[arg-type]
                company_id=c.uuid,  # type: ignore[arg-type]
            ),
            db=self.db,
        )
        return CompanyRead.model_validate(c)

    def soft_delete(self, company_id: str) -> None:
        c = self.repo.get(company_id)
        self.repo.soft_delete(c)
