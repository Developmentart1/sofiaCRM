"""Documents routes — CRUD under ``/api/v1`` plus direct upload/download under
``/api`` (no ``/v1``) to match the frontend's two network paths (see Fase 3
brief: ``documents.ts`` fetches upload/download directly against
``http://localhost:8000/api/documents`` while list/get/remove go through the
Next.js rewrite to ``/api/v1/documents``).
"""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.pagination import PaginatedResponse
from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from .schemas import DocumentRead
from .service import DocumentService


def _list(
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=200),
    search: str | None = None,
    contact_id: str | None = None,
    opportunity_id: str | None = None,
    company_id: str | None = None,
    folder: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.DOCUMENT_READ)
    return DocumentService(db).list_documents(
        search=search,
        contact_id=contact_id,
        opportunity_id=opportunity_id,
        company_id=company_id,
        folder=folder,
        page=page,
        page_size=page_size,
    )


def _get(
    doc_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.DOCUMENT_READ)
    return DocumentService(db).get_document(doc_id)


def _upload(
    file: UploadFile = File(...),
    contact_id: str | None = Form(None),
    opportunity_id: str | None = Form(None),
    company_id: str | None = Form(None),
    folder: str | None = Form(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.DOCUMENT_UPLOAD)
    return DocumentService(db).upload(
        file,
        contact_id=contact_id,
        opportunity_id=opportunity_id,
        company_id=company_id,
        folder=folder,
        current_user_id=current.id,
    )


def _download(
    doc_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.DOCUMENT_READ)
    doc, path = DocumentService(db).download_path(doc_id)
    return FileResponse(
        path=str(path),
        filename=doc.filename,
        media_type=doc.mime_type or "application/octet-stream",
    )


def _delete(
    doc_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.DOCUMENT_DELETE)
    DocumentService(db).delete_document(doc_id)


v1_router = APIRouter(prefix="/documents", tags=["documents"])
v1_router.add_api_route("", _list, methods=["GET"], response_model=PaginatedResponse[DocumentRead])
v1_router.add_api_route("/{doc_id}", _get, methods=["GET"], response_model=DocumentRead)
v1_router.add_api_route("", _upload, methods=["POST"], response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
v1_router.add_api_route("/{doc_id}/download", _download, methods=["GET"])
v1_router.add_api_route("/{doc_id}", _delete, methods=["DELETE"], status_code=status.HTTP_204_NO_CONTENT)

# Direct router (no /v1) — the frontend's upload/download fetch targets.
direct_router = APIRouter(prefix="/documents", tags=["documents-direct"])
direct_router.add_api_route("", _upload, methods=["POST"], response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
direct_router.add_api_route("/{doc_id}/download", _download, methods=["GET"])
