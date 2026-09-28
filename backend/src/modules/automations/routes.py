"""Automation routes — rule CRUD, execution history and dry-run testing."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.audit import audit_log
from core.pagination import PaginatedResponse
from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from . import engine
from .schemas import ExecutionRead, RuleCreate, RuleRead, RuleTestRequest, RuleTestResult, RuleUpdate
from .service import AutomationService

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("/rules", response_model=list[RuleRead])
def list_rules(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.AUTOMATION_READ)
    return AutomationService(db).list_rules()


@router.post("/rules", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
@audit_log("automation.create", entity_type="automation_rule")
def create_rule(
    data: RuleCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.AUTOMATION_MANAGE)
    return AutomationService(db).create_rule(data)


@router.get("/rules/{rule_id}", response_model=RuleRead)
def get_rule(
    rule_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.AUTOMATION_READ)
    return AutomationService(db).get_rule(rule_id)


@router.patch("/rules/{rule_id}", response_model=RuleRead)
@audit_log("automation.update", entity_type="automation_rule")
def update_rule(
    rule_id: str,
    data: RuleUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.AUTOMATION_MANAGE)
    return AutomationService(db).update_rule(rule_id, data)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log("automation.delete", entity_type="automation_rule")
def delete_rule(
    rule_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.AUTOMATION_MANAGE)
    AutomationService(db).delete_rule(rule_id)


@router.get("/executions", response_model=PaginatedResponse[ExecutionRead])
def list_executions(
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=200),
    rule_id: str | None = None,
    status: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.AUTOMATION_READ)
    return AutomationService(db).list_executions(
        rule_id=rule_id, status=status, page=page, page_size=page_size
    )


@router.post("/rules/{rule_id}/test", response_model=RuleTestResult)
def test_rule(
    rule_id: str,
    data: RuleTestRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.AUTOMATION_READ)
    event = engine.build_event(data.event_type, data.payload, current.organization_id)
    return engine.test_rule(rule_id, event, db, current.organization_id)
