"""Extensible action registry for the automation engine.

Each action is a callable ``handler(config: dict, event: BaseEvent, db: Session)
-> dict`` returning a small result object describing what happened (or raising
``ActionError``). Handlers run inside the engine's transaction and must NOT
commit; they ``flush`` to obtain ids and, unless the engine is in dry-run mode,
publish their own event (so downstream rules can chain, bounded by the engine's
anti-recursion depth/cycle guards).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from core.event_bus import ActivityCreated, TaskCreated, get_bus
from core.event_bus.models import BaseEvent
from modules.activities.domain import Activity
from modules.contacts.domain import Contact
from modules.opportunities.domain import Opportunity
from modules.pipelines.domain import Stage
from modules.tasks.domain import Task
from modules.users.domain import User

from .state import dry_run


class ActionError(Exception):
    """Raised by an action handler to signal a recoverable failure."""


ActionHandler = Callable[[dict[str, Any], BaseEvent, Session], dict[str, Any]]
ACTION_REGISTRY: dict[str, ActionHandler] = {}


def register_action(name: str) -> Callable[[ActionHandler], ActionHandler]:
    def decorator(fn: ActionHandler) -> ActionHandler:
        ACTION_REGISTRY[name] = fn
        return fn

    return decorator


_PLACEHOLDER = re.compile(r"\{\{\s*event\.([\w.]+)\s*\}\}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hex(value: Any) -> str | None:
    """Return a dash-less hex id (the storage format) for a UUID/str value."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value.hex
    return str(value)


def _event_value(event: BaseEvent, path: str) -> Any:
    """Resolve a (possibly dotted) path against the flat event payload."""
    stripped = path[len("event."):] if path.startswith("event.") else path
    direct = getattr(event, stripped, None)
    if direct is not None:
        return direct
    last = stripped.split(".")[-1]
    return getattr(event, last, None)


def _render(text: str, event: BaseEvent) -> str:
    def repl(match: re.Match[str]) -> str:
        value = _event_value(event, match.group(1))
        if value is None:
            return ""
        if isinstance(value, UUID):
            return value.hex
        return str(value)

    return _PLACEHOLDER.sub(repl, str(text))


def _resolve_owner(config: dict[str, Any], event: BaseEvent, db: Session) -> str | None:
    """Resolve the acting user for tasks/activities. Order: static →
    ``from_event`` → opportunity owner → event.assigned_user_id → org admin."""
    org_id = str(event.organization_id)

    static = config.get("assigned_user_id")
    if static:
        return str(static)

    from_event = config.get("from_event")
    if from_event:
        value = _event_value(event, from_event)
        if value is not None:
            # User ids are stored as dashed UUIDs (str(uuid4())).
            return str(value) if isinstance(value, UUID) else str(value)

    opp_id = getattr(event, "opportunity_id", None)
    if opp_id is not None:
        opp = (
            db.query(Opportunity)
            .filter(Opportunity.id == _hex(opp_id), Opportunity.organization_id == org_id)
            .first()
        )
        if opp is not None and opp.assigned_user_id:
            return opp.assigned_user_id

    assigned = getattr(event, "assigned_user_id", None)
    if assigned is not None:
        return str(assigned) if isinstance(assigned, UUID) else str(assigned)

    admin = (
        db.query(User)
        .filter(User.organization_id == org_id, User.role == "admin")
        .order_by(User.created_at.asc())
        .first()
    )
    return admin.id if admin is not None else None


@register_action("create_task")
def _create_task(config: dict[str, Any], event: BaseEvent, db: Session) -> dict[str, Any]:
    org_id = str(event.organization_id)
    title = _render(str(config.get("title", "Tarea")), event)
    priority = str(config.get("priority", "medium"))

    due_offset = config.get("due_offset_days")
    due_date = None
    if due_offset is not None:
        due_date = date.today() + timedelta(days=int(due_offset))

    owner = _resolve_owner(config, event, db)
    if owner is None:
        raise ActionError("could not resolve assigned_user_id for task")

    opp_id = _hex(getattr(event, "opportunity_id", None))
    task = Task(
        organization_id=org_id,
        assigned_user_id=owner,
        title=title,
        priority=priority,
        status="pending",
        due_date=due_date,
        opportunity_id=opp_id,
    )
    db.add(task)
    db.flush()

    if not dry_run.get():
        get_bus().publish(
            TaskCreated(
                organization_id=event.organization_id,
                task_id=UUID(task.id),
                title=task.title,
                due_at=None,
                assigned_user_id=UUID(owner),
                opportunity_id=UUID(opp_id) if opp_id else None,
            ),
            db=db,
        )
    return {"task_id": task.id, "title": task.title, "assigned_user_id": owner}


@register_action("create_activity")
def _create_activity(config: dict[str, Any], event: BaseEvent, db: Session) -> dict[str, Any]:
    org_id = str(event.organization_id)
    activity_type = str(config.get("type", "note"))
    subject = _render(str(config.get("subject", "Actividad")), event)
    body_raw = config.get("body")
    body = _render(str(body_raw), event) if body_raw else None

    owner = _resolve_owner(config, event, db)
    if owner is None:
        raise ActionError("could not resolve user_id for activity")

    activity = Activity(
        organization_id=org_id,
        opportunity_id=_hex(getattr(event, "opportunity_id", None)),
        contact_id=_hex(getattr(event, "contact_id", None)),
        user_id=owner,
        type=activity_type,
        subject=subject,
        body=body,
        occurred_at=_now(),
    )
    db.add(activity)
    db.flush()

    if not dry_run.get():
        get_bus().publish(
            ActivityCreated(
                organization_id=event.organization_id,
                activity_id=UUID(activity.id),
                activity_type=activity.type,
                subject=activity.subject or "",
                opportunity_id=UUID(activity.opportunity_id) if activity.opportunity_id else None,
                contact_id=UUID(activity.contact_id) if activity.contact_id else None,
                assigned_user_id=UUID(owner),
            ),
            db=db,
        )
    return {"activity_id": activity.id, "type": activity_type}


@register_action("move_stage")
def _move_stage(config: dict[str, Any], event: BaseEvent, db: Session) -> dict[str, Any]:
    org_id = str(event.organization_id)
    stage_id = config.get("stage_id")
    if not stage_id:
        raise ActionError("move_stage requires 'stage_id'")

    opp_id = getattr(event, "opportunity_id", None)
    if opp_id is None:
        raise ActionError("event has no opportunity_id")

    stage = (
        db.query(Stage)
        .filter(Stage.id == str(stage_id), Stage.organization_id == org_id)
        .first()
    )
    if stage is None:
        raise ActionError(f"stage '{stage_id}' not found in organization")

    if dry_run.get():
        return {"stage_id": str(stage_id), "simulated": True}

    from core.tenant import org_scope
    from modules.opportunities.schemas import StageTransition
    from modules.opportunities.service import OpportunityService

    with org_scope(org_id):
        OpportunityService(db).transition_stage(_hex(opp_id), StageTransition(stage_id=str(stage_id)))
    return {"stage_id": str(stage_id)}


def _set_opportunity_field(attr: str) -> ActionHandler:
    def apply(config: dict[str, Any], event: BaseEvent, db: Session) -> dict[str, Any]:
        opp_id = getattr(event, "opportunity_id", None)
        if opp_id is None:
            raise ActionError("event has no opportunity_id")
        row = (
            db.query(Opportunity)
            .filter(
                Opportunity.id == _hex(opp_id),
                Opportunity.organization_id == str(event.organization_id),
            )
            .first()
        )
        if row is None:
            raise ActionError("opportunity not found")
        setattr(row, attr, config["value"])
        db.flush()
        return {"field": f"opportunity.{attr}", "value": config["value"]}

    return apply


def _set_contact_field(attr: str) -> ActionHandler:
    def apply(config: dict[str, Any], event: BaseEvent, db: Session) -> dict[str, Any]:
        contact_id = getattr(event, "contact_id", None)
        if contact_id is None:
            raise ActionError("event has no contact_id")
        row = (
            db.query(Contact)
            .filter(
                Contact.id == _hex(contact_id),
                Contact.organization_id == str(event.organization_id),
            )
            .first()
        )
        if row is None:
            raise ActionError("contact not found")
        setattr(row, attr, config["value"])
        db.flush()
        return {"field": f"contact.{attr}", "value": config["value"]}

    return apply


# Strict allowlist of updatable fields — no free ``setattr``.
_ALLOWLIST: dict[str, ActionHandler] = {
    "opportunity.estimated_value": _set_opportunity_field("estimated_value"),
    "opportunity.priority": _set_opportunity_field("priority"),
    "opportunity.assigned_user_id": _set_opportunity_field("assigned_user_id"),
    "contact.email": _set_contact_field("email"),
    "contact.phone": _set_contact_field("phone"),
    "contact.status": _set_contact_field("status"),
}


@register_action("update_field")
def _update_field(config: dict[str, Any], event: BaseEvent, db: Session) -> dict[str, Any]:
    field = config.get("field")
    if field not in _ALLOWLIST:
        raise ActionError(
            f"field '{field}' is not updatable (allowlist: {sorted(_ALLOWLIST)})"
        )
    if "value" not in config:
        raise ActionError("update_field requires 'value'")
    return _ALLOWLIST[field](config, event, db)
