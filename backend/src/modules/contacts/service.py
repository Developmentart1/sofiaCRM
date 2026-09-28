"""Contacts service — CRUD with tenant isolation."""
import csv
from datetime import datetime, timezone
from io import StringIO
from uuid import UUID

from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.event_bus import CompanyCreated, ContactCreated, ContactUpdated, get_bus
from core.tenant import current_org_id
from modules.activities.domain import Activity
from modules.documents.domain import Document
from modules.opportunities.domain import Opportunity
from modules.tasks.domain import Task
from .domain import Company, Contact
from .schemas import CompanyCreate, ContactCreate, ContactUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ContactService:
    def __init__(self, db: Session):
        self.db = db

    # ── Companies ────────────────────────────────────────────

    def list_companies(self) -> list[Company]:
        org = current_org_id()
        return self.db.query(Company).filter(
            Company.organization_id == org, Company.deleted_at.is_(None)
        ).order_by(Company.name).all()

    def get_company(self, company_id: str) -> Company:
        org = current_org_id()
        c = self.db.query(Company).filter(
            Company.id == company_id, Company.organization_id == org
        ).first()
        if not c:
            raise NotFoundError(f"company {company_id} not found")
        return c

    def create_company(self, data: CompanyCreate) -> Company:
        org = current_org_id()
        c = Company(organization_id=org, **data.model_dump())
        self.db.add(c)
        self.db.flush()
        get_bus().publish(
            CompanyCreated(organization_id=UUID(org), company_id=UUID(c.id), name=c.name),
            db=self.db,
        )
        self.db.commit()
        return c

    # ── Contacts ─────────────────────────────────────────────

    def list_contacts(self) -> list[Contact]:
        org = current_org_id()
        return self.db.query(Contact).filter(
            Contact.organization_id == org, Contact.deleted_at.is_(None)
        ).order_by(Contact.first_name).all()

    def get_contact(self, contact_id: str) -> Contact:
        org = current_org_id()
        c = self.db.query(Contact).filter(
            Contact.id == contact_id, Contact.organization_id == org, Contact.deleted_at.is_(None)
        ).first()
        if not c:
            raise NotFoundError(f"contact {contact_id} not found")
        return c

    def create_contact(self, data: ContactCreate) -> Contact:
        org = current_org_id()
        vals = data.model_dump()
        vals["organization_id"] = org
        if vals.get("email"):
            vals["email_normalized"] = vals["email"].lower().strip()
        if vals.get("phone"):
            vals["phone_normalized"] = vals["phone"].strip().replace(" ", "")
        c = Contact(**vals)
        self.db.add(c)
        self.db.flush()
        get_bus().publish(
            ContactCreated(
                organization_id=UUID(org),
                contact_id=UUID(c.id),
                full_name=" ".join(p for p in (c.first_name, c.last_name) if p).strip(),
                email_normalized=c.email_normalized,
            ),
            db=self.db,
        )
        self.db.commit()
        return c

    def update_contact(self, contact_id: str, data: ContactUpdate) -> Contact:
        org = current_org_id()
        c = self.get_contact(contact_id)
        changed_fields: list[str] = []
        for k, v in data.model_dump(exclude_unset=True).items():
            if getattr(c, k, None) != v:
                changed_fields.append(k)
            setattr(c, k, v)
        c.updated_at = _now()
        self.db.flush()
        if changed_fields:
            get_bus().publish(
                ContactUpdated(
                    organization_id=UUID(org),
                    contact_id=UUID(c.id),
                    changed_fields=changed_fields,
                ),
                db=self.db,
            )
        self.db.commit()
        return c

    def delete_contact(self, contact_id: str) -> None:
        c = self.get_contact(contact_id)
        c.deleted_at = _now()
        c.status = "archived"
        self.db.commit()

    # ── Contact related entities ───────────────────────────────

    def list_contact_activities(self, contact_id: str) -> list[Activity]:
        org = current_org_id()
        self.get_contact(contact_id)  # validate contact exists
        return self.db.query(Activity).filter(
            Activity.organization_id == org,
            Activity.contact_id == contact_id,
        ).order_by(Activity.occurred_at.desc(), Activity.created_at.desc()).all()

    def list_contact_tasks(self, contact_id: str) -> list[Task]:
        org = current_org_id()
        self.get_contact(contact_id)  # validate contact exists
        return self.db.query(Task).filter(
            Task.organization_id == org,
            Task.contact_id == contact_id,
        ).order_by(Task.due_date, Task.created_at).all()

    def list_contact_opportunities(self, contact_id: str) -> list[Opportunity]:
        org = current_org_id()
        self.get_contact(contact_id)  # validate contact exists
        return self.db.query(Opportunity).filter(
            Opportunity.organization_id == org,
            Opportunity.contact_id == contact_id,
            Opportunity.deleted_at.is_(None),
        ).order_by(Opportunity.created_at.desc()).all()

    def list_contact_documents(self, contact_id: str) -> list[Document]:
        org = current_org_id()
        self.get_contact(contact_id)  # validate contact exists
        return self.db.query(Document).filter(
            Document.organization_id == org,
            Document.contact_id == contact_id,
            Document.deleted_at.is_(None),
        ).order_by(Document.created_at.desc()).all()

    def find_duplicates(self) -> list[dict]:
        org = current_org_id()
        # Find contacts with same email_normalized
        from sqlalchemy import func
        duplicates = (
            self.db.query(
                Contact.email_normalized,
                func.count(Contact.id).label("count"),
                func.group_concat(Contact.id).label("ids"),
                func.group_concat(Contact.first_name, ", ").label("names"),
            )
            .filter(
                Contact.organization_id == org,
                Contact.email_normalized.isnot(None),
                Contact.deleted_at.is_(None),
            )
            .group_by(Contact.email_normalized)
            .having(func.count(Contact.id) > 1)
            .all()
        )
        return [
            {
                "email": d.email_normalized,
                "count": d.count,
                "contact_ids": d.ids.split(",") if d.ids else [],
                "names": d.names,
            }
            for d in duplicates
        ]

    def import_csv(self, file_content: str) -> dict:
        org = current_org_id()
        reader = csv.DictReader(StringIO(file_content))
        created = 0
        errors = []
        for row in reader:
            try:
                data = ContactCreate(
                    first_name=row.get("first_name", ""),
                    last_name=row.get("last_name"),
                    email=row.get("email"),
                    phone=row.get("phone"),
                    mobile=row.get("mobile"),
                    position=row.get("position"),
                    company_id=row.get("company_id"),
                    rfc=row.get("rfc"),
                    legal_name=row.get("legal_name"),
                    address_street=row.get("address_street"),
                    address_city=row.get("address_city"),
                    address_state=row.get("address_state"),
                    address_zip=row.get("address_zip"),
                    tags=row.get("tags"),
                    notes=row.get("notes"),
                    source_id=row.get("source_id"),
                    type=row.get("type", "PF"),
                    status=row.get("status", "active"),
                )
                self.create_contact(data)
                created += 1
            except Exception as e:
                errors.append({"row": reader.line_num, "error": str(e)})
        return {"created": created, "errors": errors}
