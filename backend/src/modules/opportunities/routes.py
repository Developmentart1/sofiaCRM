"""Opportunity routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from .schemas import OpportunityCreate, OpportunityRead, OpportunityUpdate, StageTransition
from .service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunityRead])
def list_opportunities(
    status: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.OPPORTUNITY_READ)
    return OpportunityService(db).list_opportunities(status=status)


@router.get("/stuck", response_model=list[OpportunityRead])
def stuck_opportunities(
    days: int = Query(14, ge=1, le=365),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.OPPORTUNITY_READ)
    return OpportunityService(db).list_stuck_opportunities(days=days)


@router.get("/{opp_id}", response_model=OpportunityRead)
def get_opportunity(
    opp_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.OPPORTUNITY_READ)
    return OpportunityService(db).get_opportunity(opp_id)


@router.post("", response_model=OpportunityRead, status_code=201)
def create_opportunity(
    data: OpportunityCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.OPPORTUNITY_CREATE)
    return OpportunityService(db).create_opportunity(data)


@router.patch("/{opp_id}", response_model=OpportunityRead)
def update_opportunity(
    opp_id: str,
    data: OpportunityUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.OPPORTUNITY_UPDATE)
    return OpportunityService(db).update_opportunity(opp_id, data)


@router.post("/{opp_id}/transition", response_model=OpportunityRead)
def transition_stage(
    opp_id: str,
    data: StageTransition,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.OPPORTUNITY_CHANGE_STAGE)
    return OpportunityService(db).transition_stage(opp_id, data)


@router.delete("/{opp_id}", status_code=204)
def delete_opportunity(
    opp_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.OPPORTUNITY_DELETE)
    OpportunityService(db).delete_opportunity(opp_id)
