"""Contacts (PF/PM) and Companies routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from core.audit import audit_log
from core.errors import ForbiddenError
from core.event_bus import get_bus
from core.rbac import Permission, role_has
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
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
from .service import CompanyService, ContactService

router = APIRouter(tags=["contacts"])


def _contact(db):
    return ContactService(db, get_bus())


def _company(db):
    return CompanyService(db, get_bus())


def _check(role: str, perm: Permission) -> None:
    if not role_has(role, perm):
        raise ForbiddenError(f"role lacks {perm.value}")


# ---- Companies ----


@router.get("/companies", response_model=list[CompanyRead])
def list_companies(current: CurrentUserDep, db: DbSessionDep) -> list[CompanyRead]:
    _check(current.role, Permission.CONTACT_READ)
    return _company(db).list_companies()


@router.post("/companies", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
@audit_log("company.create", entity_type="company")
def create_company(
    payload: CompanyCreate, current: CurrentUserDep, db: DbSessionDep
) -> CompanyRead:
    _check(current.role, Permission.CONTACT_CREATE)
    return _company(db).create(payload)


@router.get("/companies/{company_id}", response_model=CompanyRead)
def get_company(company_id: str, current: CurrentUserDep, db: DbSessionDep) -> CompanyRead:
    _check(current.role, Permission.CONTACT_READ)
    return _company(db).get(company_id)


@router.patch("/companies/{company_id}", response_model=CompanyRead)
@audit_log("company.update", entity_type="company")
def update_company(
    company_id: str, payload: CompanyUpdate, current: CurrentUserDep, db: DbSessionDep
) -> CompanyRead:
    _check(current.role, Permission.CONTACT_UPDATE)
    return _company(db).update(company_id, payload)


# ---- Contacts ----


@router.get("/contacts", response_model=list[ContactRead])
def list_contacts(current: CurrentUserDep, db: DbSessionDep) -> list[ContactRead]:
    _check(current.role, Permission.CONTACT_READ)
    return _contact(db).list_contacts()


@router.post("/contacts", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
@audit_log("contact.create", entity_type="contact")
def create_contact(
    payload: ContactCreate, current: CurrentUserDep, db: DbSessionDep
) -> ContactRead:
    _check(current.role, Permission.CONTACT_CREATE)
    return _contact(db).create(payload)


@router.get("/contacts/duplicates", response_model=list[DuplicateCandidate])
def find_duplicates(
    email: str | None = None,
    phone: str | None = None,
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> list[DuplicateCandidate]:
    _check(current.role, Permission.CONTACT_READ)
    return _contact(db).find_duplicates(email=email, phone=phone)


@router.get("/contacts/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: str, current: CurrentUserDep, db: DbSessionDep) -> ContactRead:
    _check(current.role, Permission.CONTACT_READ)
    return _contact(db).get(contact_id)


@router.patch("/contacts/{contact_id}", response_model=ContactRead)
@audit_log("contact.update", entity_type="contact")
def update_contact(
    contact_id: str, payload: ContactUpdate, current: CurrentUserDep, db: DbSessionDep
) -> ContactRead:
    _check(current.role, Permission.CONTACT_UPDATE)
    return _contact(db).update(contact_id, payload)


@router.post("/contacts/merge", response_model=ContactRead)
@audit_log("contact.merge", entity_type="contact")
def merge_contacts(
    payload: ContactMergeRequest, current: CurrentUserDep, db: DbSessionDep
) -> ContactRead:
    _check(current.role, Permission.CONTACT_MERGE)
    return _contact(db).merge(payload)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log("contact.soft_delete", entity_type="contact")
def soft_delete_contact(
    contact_id: str, current: CurrentUserDep, db: DbSessionDep
) -> None:
    _check(current.role, Permission.CONTACT_DELETE)
    _contact(db).soft_delete(contact_id)
