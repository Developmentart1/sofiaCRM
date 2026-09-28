"""Document service. Persists bytes on local FS + DB row, mints signed URL."""
from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import ValidationError
from core.event_bus import DocumentUploaded, SyncEventBus
from core.security import sign_storage_url
from core.tenant import current_org_id
from .domain import Document
from .repository import DocumentRepository
from .schemas import DocumentMetadata, DocumentRead


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._\-]")


def _safe_name(name: str) -> str:
    s = _SAFE_NAME_RE.sub("_", name).strip("_")
    return s or "file"


class DocumentService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = DocumentRepository(db)
        self.settings = get_settings()

    def storage_root(self) -> Path:
        return self.settings.storage_path

    def list(
        self,
        *,
        contact_id: str | None = None,
        opportunity_id: str | None = None,
    ) -> list[DocumentRead]:
        return [
            DocumentRead.model_validate(d)
            for d in self.repo.list_filtered(contact_id=contact_id, opportunity_id=opportunity_id)
        ]

    def get(self, doc_id: str) -> DocumentRead:
        return DocumentRead.model_validate(self.repo.get(doc_id))

    async def upload(
        self,
        file: UploadFile,
        *,
        contact_id: str | None,
        opportunity_id: str | None,
        description: str | None,
        uploaded_by: str,
    ) -> DocumentMetadata:
        """Persist the file under backend/storage/<org>/<id>__<name>.

        Stream-friendly: bytes are read in chunks and written incrementally.
        """
        org = current_org_id()
        safe = _safe_name(file.filename or "upload.bin")
        doc_id = str(uuid4())
        org_dir = self.storage_root() / org
        org_dir.mkdir(parents=True, exist_ok=True)
        stored = org_dir / f"{doc_id}__{safe}"
        size = 0
        with stored.open("wb") as fh:
            while chunk := await file.read(64 * 1024):
                size += len(chunk)
                fh.write(chunk)
        if size == 0:
            stored.unlink(missing_ok=True)
            raise ValidationError("uploaded file is empty")
        rel_path = f"{org}/{stored.name}"
        mime = file.content_type or "application/octet-stream"
        d = self.repo.create(
            filename=file.filename or safe,
            safe_name=safe,
            storage_path=rel_path,
            mime_type=mime,
            size_bytes=size,
            description=description,
            contact_id=contact_id,
            opportunity_id=opportunity_id,
            uploaded_by=uploaded_by,
        )
        self.bus.publish(
            DocumentUploaded(
                organization_id=UUID(d.organization_id),
                document_id=d.uuid,
                filename=d.filename,
                size_bytes=d.size_bytes,
                contact_id=UUID(d.contact_id) if d.contact_id else None,
                opportunity_id=UUID(d.opportunity_id) if d.opportunity_id else None,
            ),
            db=self.db,
        )
        token = sign_storage_url(d.storage_path)
        return DocumentMetadata(
            id=d.uuid,
            filename=d.filename,
            mime_type=d.mime_type,
            size_bytes=d.size_bytes,
            download_url=f"/api/v1/documents/{d.id}/download?t={token}",
            expires_in_seconds=self.settings.storage_url_max_age_seconds,
        )

    def resolve_storage_path(self, signed_token: str) -> Path:
        """Verify the signed token, then make sure the decoded relative path
        starts with the caller's organization_id. Raises on mismatch.
        """
        from core.security import verify_storage_url
        from core.errors import UnauthorizedError

        rel = verify_storage_url(signed_token)
        # rel looks like "<org_id>/<doc_id>__<name>"
        org = current_org_id()
        prefix = f"{org}/"
        if not rel.startswith(prefix):
            raise UnauthorizedError("signed url does not belong to current organization")
        full = self.storage_root() / rel
        # Defensive: ensure resolved path is under storage_root.
        resolved = full.resolve()
        if not str(resolved).startswith(str(self.storage_root().resolve())):
            raise UnauthorizedError("storage path escapes storage root")
        return resolved

    def delete(self, doc_id: str) -> None:
        d = self.repo.get(doc_id)
        try:
            (self.storage_root() / d.storage_path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        self.repo.delete(d)
