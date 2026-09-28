"""Document routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from core.audit import audit_log
from core.errors import ForbiddenError, NotFoundError
from core.event_bus import get_bus
from core.rbac import Permission, role_has
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
from .schemas import DocumentMetadata, DocumentRead
from .service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def _service(db):
    return DocumentService(db, get_bus())


@router.get("", response_model=list[DocumentRead])
def list_documents(
    contact_id: UUID | None = None,
    opportunity_id: UUID | None = None,
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> list[DocumentRead]:
    if not role_has(current.role, Permission.DOCUMENT_READ):
        raise ForbiddenError("role lacks document:read")
    return _service(db).list(
        contact_id=str(contact_id) if contact_id else None,
        opportunity_id=str(opportunity_id) if opportunity_id else None,
    )


@router.post("/upload", response_model=DocumentMetadata, status_code=status.HTTP_201_CREATED)
@audit_log("document.upload", entity_type="document")
async def upload_document(
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    contact_id: UUID | None = Form(default=None),
    opportunity_id: UUID | None = Form(default=None),
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> DocumentMetadata:
    if not role_has(current.role, Permission.DOCUMENT_UPLOAD):
        raise ForbiddenError("role lacks document:upload")
    return await _service(db).upload(
        file,
        contact_id=str(contact_id) if contact_id else None,
        opportunity_id=str(opportunity_id) if opportunity_id else None,
        description=description,
        uploaded_by=current.id,
    )


@router.get("/{doc_id}/download")
def download_document(
    doc_id: str,
    t: str = Query(..., description="signed token returned by upload"),
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> FileResponse:
    if not role_has(current.role, Permission.DOCUMENT_READ):
        raise ForbiddenError("role lacks document:read")
    # Validate the document exists in the caller's org.
    _service(db).get(doc_id)
    path = _service(db).resolve_storage_path(t)
    if not path.exists():
        raise NotFoundError("stored file not found on disk")
    return FileResponse(path=path, filename=path.name)
