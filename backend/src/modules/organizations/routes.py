"""Organization routes — bootstrap (signup) and read/update (auth)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.audit import audit_log
from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from modules.organizations.schemas import OrganizationCreate, OrganizationRead, OrganizationUpdate
from modules.organizations.service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/bootstrap", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
@audit_log("org.bootstrap", entity_type="organization")
def bootstrap_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db_session),
) -> OrganizationRead:
    org, _admin = OrganizationService(db).bootstrap(payload)
    db.commit()
    return OrganizationRead.model_validate(org)


@router.get("/me", response_model=OrganizationRead)
def get_my_organization(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> OrganizationRead:
    require_permission(current.role, Permission.ORG_READ)
    return OrganizationService(db).get(current.organization_id)


@router.patch("/me", response_model=OrganizationRead)
@audit_log("org.update", entity_type="organization")
def update_my_organization(
    payload: OrganizationUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> OrganizationRead:
    require_permission(current.role, Permission.ORG_UPDATE)
    return OrganizationService(db).update(current.organization_id, payload)
