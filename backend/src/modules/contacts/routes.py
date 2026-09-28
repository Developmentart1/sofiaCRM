"""Contacts routes — CRUD for contacts and companies."""
from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from .schemas import CompanyCreate, CompanyRead, ContactCreate, ContactRead, ContactUpdate
from .service import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


# ── Companies ────────────────────────────────────────────

@router.get("/companies", response_model=list[CompanyRead])
def list_companies(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).list_companies()


@router.post("/companies", response_model=CompanyRead, status_code=201)
def create_company(
    data: CompanyCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_CREATE)
    return ContactService(db).create_company(data)


# ── Contacts ─────────────────────────────────────────────

@router.get("", response_model=list[ContactRead])
def list_contacts(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).list_contacts()


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).get_contact(contact_id)


@router.post("", response_model=ContactRead, status_code=201)
def create_contact(
    data: ContactCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_CREATE)
    return ContactService(db).create_contact(data)


@router.patch("/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: str,
    data: ContactUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_UPDATE)
    return ContactService(db).update_contact(contact_id, data)


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_DELETE)
    ContactService(db).delete_contact(contact_id)


# ── Sub-resources ─────────────────────────────────────────────

@router.get("/{contact_id}/activities")
def list_contact_activities(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    from modules.activities.schemas import ActivityRead
    activities = ContactService(db).list_contact_activities(contact_id)
    return [ActivityRead.model_validate(a) for a in activities]


@router.get("/{contact_id}/tasks")
def list_contact_tasks(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    from modules.tasks.schemas import TaskRead
    tasks = ContactService(db).list_contact_tasks(contact_id)
    return [TaskRead.model_validate(t) for t in tasks]


@router.get("/{contact_id}/opportunities")
def list_contact_opportunities(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    from modules.opportunities.schemas import OpportunityRead
    opportunities = ContactService(db).list_contact_opportunities(contact_id)
    return [OpportunityRead.model_validate(o) for o in opportunities]


@router.get("/{contact_id}/documents")
def list_contact_documents(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    from modules.documents.schemas import DocumentRead
    documents = ContactService(db).list_contact_documents(contact_id)
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/duplicates")
def find_duplicate_contacts(
    email: str | None = None,
    phone: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).find_duplicates()


@router.post("/import", status_code=201)
async def import_contacts(
    file: UploadFile,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_CREATE)
    contents = await file.read()
    file_content = contents.decode("utf-8")
    return ContactService(db).import_csv(file_content)
