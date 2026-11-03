"""ARM routes - LLM-assisted relation management."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from .service import ArmService

router = APIRouter(prefix="/arm", tags=["arm"])


@router.post("/contacts/{contact_id}/draft-followup")
def draft_followup(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return {"text": ArmService(db).draft_followup(contact_id)}


@router.post("/contacts/{contact_id}/summarize")
def summarize_relation(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return {"text": ArmService(db).summarize_relation(contact_id)}
