"""Document repository — scoped by organization_id."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, doc_id: str) -> Document:
        org = current_org_id()
        stmt = select(Document).where(Document.id == doc_id, Document.organization_id == org)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"document {doc_id} not found")
        return row

    def list_filtered(
        self,
        *,
        contact_id: str | None = None,
        opportunity_id: str | None = None,
        limit: int = 100,
    ) -> list[Document]:
        org = current_org_id()
        stmt = select(Document).where(Document.organization_id == org)
        if contact_id is not None:
            stmt = stmt.where(Document.contact_id == contact_id)
        if opportunity_id is not None:
            stmt = stmt.where(Document.opportunity_id == opportunity_id)
        stmt = stmt.order_by(Document.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **kwargs) -> Document:
        org = current_org_id()
        d = Document(organization_id=org, **kwargs)
        self.db.add(d)
        self.db.flush()
        return d

    def delete(self, d: Document) -> None:
        self.db.delete(d)
        self.db.flush()
