"""Automation routes."""
from __future__ import annotations

from fastapi import APIRouter, Query, status

from core.audit import audit_log
from core.errors import ForbiddenError
from core.event_bus import get_bus, SyncEventBus
from core.rbac import Permission, role_has
from core.tenant import current_org_id
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
from .engine import AutomationEngine
from .schemas import (
    AutomationExecutionRead,
    AutomationRuleCreate,
    AutomationRuleRead,
)
from .service import AutomationService

router = APIRouter(prefix="/automation", tags=["automation"])


def _service(db) -> AutomationService:
    return AutomationService(db, get_bus())


def _require_admin_or_director(role: str) -> None:
    if not role_has(role, Permission.AUTOMATION_MANAGE):
        raise ForbiddenError("role lacks automation:manage")


@router.get("/rules", response_model=list[AutomationRuleRead])
def list_rules(
    current: CurrentUserDep, db: DbSessionDep
) -> list[AutomationRuleRead]:
    if not role_has(current.role, Permission.AUTOMATION_READ):
        raise ForbiddenError("role lacks automation:read")
    return _service(db).list_rules()


@router.post("/rules", response_model=AutomationRuleRead, status_code=status.HTTP_201_CREATED)
@audit_log("automation.rule.create", entity_type="automation_rule")
def create_rule(
    payload: AutomationRuleCreate, current: CurrentUserDep, db: DbSessionDep
) -> AutomationRuleRead:
    _require_admin_or_director(current.role)
    return _service(db).create_rule(payload)


@router.get("/rules/{rule_id}", response_model=AutomationRuleRead)
def get_rule(
    rule_id: str, current: CurrentUserDep, db: DbSessionDep
) -> AutomationRuleRead:
    if not role_has(current.role, Permission.AUTOMATION_READ):
        raise ForbiddenError("role lacks automation:read")
    return _service(db).get_rule(rule_id)


@router.get("/executions", response_model=list[AutomationExecutionRead])
def list_executions(
    limit: int = Query(default=50, ge=1, le=200),
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> list[AutomationExecutionRead]:
    if not role_has(current.role, Permission.AUTOMATION_READ):
        raise ForbiddenError("role lacks automation:read")
    return _service(db).last_executions(limit=limit)


def register_event_subscribers(bus: SyncEventBus) -> None:
    """Hooked by main.py: each event type triggers the AutomationEngine.

    Subscriber is per-event because the handlers must call the engine with
    the right Pydantic subclass; since we receive ``BaseEvent`` we dispatch
    on event_type which is enough for routing.
    """
    # We register a single wildcard subscriber via the bus's subscribe API:
    # because the bus keys on event_type, we register each concrete type.
    from .engine import AutomationEngine  # noqa: F401  (already imported)

    from core.event_bus.models import EventEnvelope
    from pydantic import TypeAdapter

    adapter: TypeAdapter = TypeAdapter(EventEnvelope)

    def _dispatch(event, db):
        engine = AutomationEngine(db)
        engine.handle_event(event, depth=0)

    # Subscribe to every concrete event_type currently supported by the bus.
    for typ in (
        "contact.created",
        "contact.updated",
        "contact.merged",
        "company.created",
        "company.updated",
        "pipeline.created",
        "stage.created",
        "opportunity.created",
        "opportunity.stage_changed",
        "opportunity.assignee_changed",
        "opportunity.value_changed",
        "opportunity.won",
        "opportunity.lost",
        "opportunity.discarded",
        "task.created",
        "task.completed",
        "task.overdue",
        "activity.created",
        "document.uploaded",
    ):
        bus.subscribe(typ, _dispatch)
