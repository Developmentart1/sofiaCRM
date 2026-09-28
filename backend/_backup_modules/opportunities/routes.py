"""Opportunities routes. CRUD + stage transitions + close/reopen."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from core.audit import audit_log
from core.errors import ForbiddenError
from core.event_bus import get_bus
from core.rbac import Permission, role_has
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
from .schemas import (
    LeadSourceCreate,
    LeadSourceRead,
    LostReasonCreate,
    LostReasonRead,
    OpportunityCloseLost,
    OpportunityCloseWon,
    OpportunityCreate,
    OpportunityRead,
    OpportunityStageChange,
    OpportunityUpdate,
)
from .service import LeadSourceService, LostReasonService, OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])
aux_router = APIRouter(prefix="/catalogs", tags=["catalogs"])


def _service(db):
    return OpportunityService(db, get_bus())


@router.get("", response_model=list[OpportunityRead])
def list_opportunities(
    current: CurrentUserDep,
    db: DbSessionDep,
    status_filter: str | None = Query(default=None, alias="status"),
    pipeline_id: UUID | None = None,
    stage_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
) -> list[OpportunityRead]:
    role = current.role
    if not (role_has(role, Permission.OPPORTUNITY_READ)):
        raise ForbiddenError("role lacks opportunity:read")
    return _service(db).list(
        status=status_filter,
        pipeline_id=str(pipeline_id) if pipeline_id else None,
        stage_id=str(stage_id) if stage_id else None,
        assigned_user_id=str(assigned_user_id) if assigned_user_id else None,
    )


@router.post("", response_model=OpportunityRead, status_code=status.HTTP_201_CREATED)
@audit_log("opportunity.create", entity_type="opportunity")
def create_opportunity(
    payload: OpportunityCreate, current: CurrentUserDep, db: DbSessionDep
) -> OpportunityRead:
    if not role_has(current.role, Permission.OPPORTUNITY_CREATE):
        raise ForbiddenError("role lacks opportunity:create")
    return _service(db).create(payload)


@router.get("/{opp_id}", response_model=OpportunityRead)
def get_opportunity(opp_id: str, current: CurrentUserDep, db: DbSessionDep) -> OpportunityRead:
    if not role_has(current.role, Permission.OPPORTUNITY_READ):
        raise ForbiddenError("role lacks opportunity:read")
    return _service(db).get(opp_id)


@router.patch("/{opp_id}", response_model=OpportunityRead)
@audit_log("opportunity.update", entity_type="opportunity")
def update_opportunity(
    opp_id: str,
    payload: OpportunityUpdate,
    current: CurrentUserDep,
    db: DbSessionDep,
) -> OpportunityRead:
    if not role_has(current.role, Permission.OPPORTUNITY_UPDATE):
        raise ForbiddenError("role lacks opportunity:update")
    return _service(db).update(opp_id, payload, actor_role=current.role)


@router.post("/{opp_id}/stage", response_model=OpportunityRead)
@audit_log("opportunity.stage_changed", entity_type="opportunity")
def change_stage(
    opp_id: str,
    payload: OpportunityStageChange,
    current: CurrentUserDep,
    db: DbSessionDep,
) -> OpportunityRead:
    if not role_has(current.role, Permission.OPPORTUNITY_CHANGE_STAGE):
        raise ForbiddenError("role lacks opportunity:change_stage")
    return _service(db).change_stage(opp_id, payload)


@router.post("/{opp_id}/close-lost", response_model=OpportunityRead)
@audit_log("opportunity.lost", entity_type="opportunity")
def close_lost(
    opp_id: str,
    payload: OpportunityCloseLost,
    current: CurrentUserDep,
    db: DbSessionDep,
) -> OpportunityRead:
    if not role_has(current.role, Permission.OPPORTUNITY_CLOSE):
        raise ForbiddenError("role lacks opportunity:close")
    return _service(db).close_lost(opp_id, payload, actor_role=current.role)


@router.post("/{opp_id}/close-won", response_model=OpportunityRead)
@audit_log("opportunity.won", entity_type="opportunity")
def close_won(
    opp_id: str,
    payload: OpportunityCloseWon,
    current: CurrentUserDep,
    db: DbSessionDep,
) -> OpportunityRead:
    if not role_has(current.role, Permission.OPPORTUNITY_CLOSE):
        raise ForbiddenError("role lacks opportunity:close")
    return _service(db).close_won(opp_id, payload)


@router.post("/{opp_id}/discard", response_model=OpportunityRead)
@audit_log("opportunity.discarded", entity_type="opportunity")
def discard_opportunity(
    opp_id: str,
    reason: str = Query(min_length=1, max_length=500),
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> OpportunityRead:
    if not role_has(current.role, Permission.OPPORTUNITY_UPDATE):
        raise ForbiddenError("role lacks opportunity:update")
    return _service(db).discard(opp_id, reason)


@router.post("/{opp_id}/reopen", response_model=OpportunityRead)
@audit_log("opportunity.reopen", entity_type="opportunity")
def reopen(opp_id: str, current: CurrentUserDep, db: DbSessionDep) -> OpportunityRead:
    if not role_has(current.role, Permission.OPPORTUNITY_CREATE):
        raise ForbiddenError("role lacks opportunities.reopen permission")
    return _service(db).reopen(opp_id, actor_role=current.role)


@router.delete("/{opp_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log("opportunity.soft_delete", entity_type="opportunity")
def soft_delete_opportunity(opp_id: str, current: CurrentUserDep, db: DbSessionDep) -> None:
    if not role_has(current.role, Permission.OPPORTUNITY_UPDATE):
        raise ForbiddenError("role lacks opportunity:update")
    _service(db).soft_delete(opp_id)


# ---- Lost reasons + Lead sources catalog (mounted under /catalogs) ----


@aux_router.get("/lost-reasons", response_model=list[LostReasonRead])
def list_lost_reasons(current: CurrentUserDep, db: DbSessionDep) -> list[LostReasonRead]:
    if not role_has(current.role, Permission.OPPORTUNITY_READ):
        raise ForbiddenError("role lacks opportunity:read")
    return LostReasonService(db).list()


@aux_router.post(
    "/lost-reasons", response_model=LostReasonRead, status_code=status.HTTP_201_CREATED
)
@audit_log("lost_reason.create", entity_type="lost_reason")
def create_lost_reason(
    payload: LostReasonCreate, current: CurrentUserDep, db: DbSessionDep
) -> LostReasonRead:
    if not role_has(current.role, Permission.OPPORTUNITY_UPDATE):
        raise ForbiddenError("role lacks opportunity:update")
    return LostReasonService(db).create(payload)


@aux_router.get("/lead-sources", response_model=list[LeadSourceRead])
def list_lead_sources(current: CurrentUserDep, db: DbSessionDep) -> list[LeadSourceRead]:
    if not role_has(current.role, Permission.OPPORTUNITY_READ):
        raise ForbiddenError("role lacks opportunity:read")
    return LeadSourceService(db).list()


@aux_router.post(
    "/lead-sources", response_model=LeadSourceRead, status_code=status.HTTP_201_CREATED
)
@audit_log("lead_source.create", entity_type="lead_source")
def create_lead_source(
    payload: LeadSourceCreate, current: CurrentUserDep, db: DbSessionDep
) -> LeadSourceRead:
    if not role_has(current.role, Permission.OPPORTUNITY_UPDATE):
        raise ForbiddenError("role lacks opportunity:update")
    return LeadSourceService(db).create(payload)
