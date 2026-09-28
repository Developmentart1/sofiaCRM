"""Documents service — upload/download/list/delete with tenant isolation.

The module exposes two network prefixes (see ``routes.py`` and the Fase 3
brief): CRUD under ``/api/v1/documents`` and direct ``/api/documents`` for the
frontend's upload/download fetches. Storage layout:
``{storage_root}/{org_id}/{uuid}_{safe_name}``.
"""
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import NotFoundError, ValidationError
from core.event_bus import DocumentUploaded, get_bus
from core.pagination import PaginatedResponse
from core.tenant import current_org_id
from modules.contacts.domain import Company, Contact
from modules.opportunities.domain import Opportunity
from modules.users.domain import User
from .domain import Document
from .schemas import DocumentRead

_DOWNLOAD_URL = "/api/documents/{id}/download"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_name(filename: str) -> str:
    """Filesystem-safe basename of the original upload name."""
    name = Path(filename).name
    name = re.sub(r"[^\w.\-]", "_", name).strip("._") or "file"
    return name[:200]


class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    # ── helpers ──────────────────────────────────────────

    def _validate_refs(
        self,
        contact_id: str | None,
        opportunity_id: str | None,
        company_id: str | None,
    ) -> None:
        org = current_org_id()
        if contact_id:
            if not self.db.query(Contact).filter(
                Contact.id == contact_id,
                Contact.organization_id == org,
                Contact.deleted_at.is_(None),
            ).first():
                raise NotFoundError(f"contact '{contact_id}' not found")
        if company_id:
            if not self.db.query(Company).filter(
                Company.id == company_id,
                Company.organization_id == org,
                Company.deleted_at.is_(None),
            ).first():
                raise NotFoundError(f"company '{company_id}' not found")
        if opportunity_id:
            if not self.db.query(Opportunity).filter(
                Opportunity.id == opportunity_id,
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
            ).first():
                raise NotFoundError(f"opportunity '{opportunity_id}' not found")

    def _base_query(self):
        org = current_org_id()
        return (
            self.db.query(
                Document,
                Contact.first_name,
                Contact.last_name,
                Opportunity.name,
                Company.name,
                User.full_name,
            )
            .outerjoin(Contact, and_(Contact.id == Document.contact_id, Contact.organization_id == org))
            .outerjoin(
                Opportunity, and_(Opportunity.id == Document.opportunity_id, Opportunity.organization_id == org)
            )
            .outerjoin(Company, and_(Company.id == Document.company_id, Company.organization_id == org))
            .outerjoin(User, User.id == Document.uploaded_by_id)
            .filter(Document.organization_id == org, Document.deleted_at.is_(None))
        )

    def _to_read(
        self,
        doc: Document,
        contact_first: str | None,
        contact_last: str | None,
        opp_name: str | None,
        company_name: str | None,
        uploader_name: str | None,
    ) -> DocumentRead:
        contact_name = " ".join(p for p in (contact_first, contact_last) if p).strip() or None
        return DocumentRead(
            id=doc.id,
            name=doc.filename,
            mime_type=doc.mime_type,
            size=doc.size_bytes,
            url=_DOWNLOAD_URL.format(id=doc.id),
            contact_id=doc.contact_id,
            contact_name=contact_name,
            opportunity_id=doc.opportunity_id,
            opportunity_name=opp_name,
            company_id=doc.company_id,
            company_name=company_name,
            uploaded_by_id=doc.uploaded_by_id,
            uploaded_by_name=uploader_name,
            folder=doc.folder,
            created_at=doc.created_at,
        )

    def _read_one(self, doc_id: str) -> DocumentRead:
        row = self._base_query().filter(Document.id == doc_id).first()
        if not row:
            raise NotFoundError(f"document '{doc_id}' not found")
        return self._to_read(*row)

    def _get_orm(self, doc_id: str) -> Document:
        org = current_org_id()
        doc = self.db.query(Document).filter(
            Document.id == doc_id,
            Document.organization_id == org,
            Document.deleted_at.is_(None),
        ).first()
        if not doc:
            raise NotFoundError(f"document '{doc_id}' not found")
        return doc

    # ── operations ───────────────────────────────────────

    def upload(
        self,
        file: UploadFile,
        *,
        contact_id: str | None,
        opportunity_id: str | None,
        company_id: str | None,
        folder: str | None,
        current_user_id: str,
    ) -> DocumentRead:
        org = current_org_id()
        self._validate_refs(contact_id, opportunity_id, company_id)

        settings = get_settings()
        filename = Path(file.filename or "file").name
        safe_name = _safe_name(filename)
        mime_type = file.content_type or None
        folder = (folder or "").strip() or None

        doc_id = uuid4().hex
        dest_dir = settings.storage_path / org
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{doc_id}_{safe_name}"

        size_bytes = 0
        chunk_size = 1024 * 1024
        try:
            with dest.open("wb") as out:
                while True:
                    chunk = file.file.read(chunk_size)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > settings.max_upload_size_bytes:
                        raise ValidationError(
                            f"file exceeds the maximum size of "
                            f"{settings.max_upload_size_bytes} bytes",
                            details={"max_bytes": settings.max_upload_size_bytes},
                        )
                    out.write(chunk)
        except ValidationError:
            dest.unlink(missing_ok=True)
            raise
        except Exception:
            dest.unlink(missing_ok=True)
            raise

        doc = Document(
            id=doc_id,
            organization_id=org,
            contact_id=contact_id,
            company_id=company_id,
            opportunity_id=opportunity_id,
            uploaded_by_id=current_user_id,
            filename=filename,
            safe_name=safe_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_path=str(dest),
            folder=folder,
        )
        self.db.add(doc)
        self.db.flush()
        get_bus().publish(
            DocumentUploaded(
                organization_id=UUID(org),
                document_id=UUID(doc.id),
                filename=doc.filename,
                size_bytes=doc.size_bytes,
                contact_id=UUID(contact_id) if contact_id else None,
                opportunity_id=UUID(opportunity_id) if opportunity_id else None,
            ),
            db=self.db,
        )
        self.db.commit()
        return self._read_one(doc.id)

    def list_documents(
        self,
        *,
        search: str | None = None,
        contact_id: str | None = None,
        opportunity_id: str | None = None,
        company_id: str | None = None,
        folder: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[DocumentRead]:
        q = self._base_query()
        if search:
            like = f"%{search}%"
            q = q.filter(or_(Document.filename.ilike(like), Document.safe_name.ilike(like)))
        if contact_id:
            q = q.filter(Document.contact_id == contact_id)
        if opportunity_id:
            q = q.filter(Document.opportunity_id == opportunity_id)
        if company_id:
            q = q.filter(Document.company_id == company_id)
        if folder:
            q = q.filter(Document.folder == folder)

        total = q.count()
        rows = (
            q.order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items = [self._to_read(*row) for row in rows]
        return PaginatedResponse.of(items=items, total=total, page=page, page_size=page_size)

    def get_document(self, doc_id: str) -> DocumentRead:
        return self._read_one(doc_id)

    def download_path(self, doc_id: str) -> tuple[Document, Path]:
        doc = self._get_orm(doc_id)
        path = Path(doc.storage_path)
        if not path.is_file():
            raise NotFoundError(f"document '{doc_id}' file is missing from storage")
        return doc, path

    def delete_document(self, doc_id: str) -> None:
        doc = self._get_orm(doc_id)
        doc.deleted_at = _now()
        self.db.commit()
