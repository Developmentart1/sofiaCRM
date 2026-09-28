"""Automation engine: evaluates rules against events and executes their actions.

``handle_event`` is subscribed to every event type in ``models.EventEnvelope``.
It is tenant-scoped by the event's ``organization_id`` (never the request's org
context), and it never propagates exceptions: every failure is recorded on an
``AutomationExecution`` row.

Anti-recursion (implemented with ContextVars, since event payloads are
``extra="forbid"``):
  1. ``depth`` caps the total nesting depth. When a rule's actions publish events
     that trigger further rules, the depth grows; a rule whose ``max_depth`` is
     reached is recorded as ``skipped``.
  2. ``in_progress`` tracks the set of rule ids on the current call stack and
     breaks cycles (A→B→A) even when neither rule exceeds its own max_depth.
"""
from __future__ import annotations

import json
import logging
import typing
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from core.errors import NotFoundError, ValidationError
from core.event_bus.models import BaseEvent, EventEnvelope
from .actions import ACTION_REGISTRY, ActionError
from .conditions import evaluate_conditions
from .domain import AutomationAction, AutomationExecution, AutomationRule
from .state import depth, dry_run, in_progress

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _event_aggregate_id(event: BaseEvent) -> str:
    for field in (
        "contact_id",
        "company_id",
        "opportunity_id",
        "pipeline_id",
        "stage_id",
        "task_id",
        "activity_id",
        "document_id",
        "winner_id",
    ):
        value = getattr(event, field, None)
        if value is not None:
            return value.hex if isinstance(value, UUID) else str(value)
    return str(event.organization_id)


def all_event_classes() -> list[type[BaseEvent]]:
    """Introspect the ``EventEnvelope`` discriminated union to list all events."""
    union = typing.get_args(EventEnvelope)[0]
    return list(typing.get_args(union))


def all_event_types() -> set[str]:
    return {cls.model_fields["event_type"].default for cls in all_event_classes()}


def build_event(event_type: str, payload: dict[str, Any], org_id: str) -> BaseEvent:
    """Re-hydrate a synthetic event for the dry-run endpoint (422 on bad payload)."""
    adapter: TypeAdapter[EventEnvelope] = TypeAdapter(EventEnvelope)
    data: dict[str, Any] = {"event_type": event_type, "organization_id": org_id, **payload}
    try:
        return adapter.validate_python(data)
    except Exception as exc:  # noqa: BLE001 — pydantic validation errors
        raise ValidationError(
            f"invalid synthetic event for '{event_type}'",
            details={"error": str(exc)},
        ) from exc


def _load_conditions(rule: AutomationRule) -> list[dict[str, Any]]:
    if not rule.conditions_json:
        return []
    try:
        parsed = json.loads(rule.conditions_json)
    except (ValueError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _load_config(action: AutomationAction) -> dict[str, Any]:
    try:
        parsed = json.loads(action.config_json)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_actions(rule_id: str, db: Session) -> list[AutomationAction]:
    return (
        db.query(AutomationAction)
        .filter(AutomationAction.rule_id == rule_id)
        .order_by(AutomationAction.position.asc(), AutomationAction.id.asc())
        .all()
    )


def _record(
    rule: AutomationRule,
    event: BaseEvent,
    status: str,
    depth_value: int,
    result: dict[str, Any] | None,
    error: str | None,
    started_at: datetime,
    db: Session,
) -> dict[str, Any]:
    execution = AutomationExecution(
        rule_id=rule.id,
        trigger_event_id=_event_aggregate_id(event),
        status=status,
        depth=depth_value,
        result_json=json.dumps(result) if result is not None else None,
        error=error,
        started_at=started_at,
        finished_at=_now(),
    )
    db.add(execution)
    db.flush()
    return {"execution_id": execution.id, "status": status, "result": result}


def _run_single(
    rule: AutomationRule, event: BaseEvent, db: Session, *, is_dry_run: bool
) -> dict[str, Any]:
    started_at = _now()
    current_depth = depth.get()

    # Anti-recursion guards (not applied to explicit dry-run tests).
    if not is_dry_run:
        if rule.id in in_progress.get():
            return _record(rule, event, "skipped", current_depth, {"reason": "cycle"}, None, started_at, db)
        max_depth = rule.max_depth if rule.max_depth is not None else 5
        if current_depth >= max_depth:
            return _record(rule, event, "skipped", current_depth, {"reason": "max_depth"}, None, started_at, db)

    if not evaluate_conditions(_load_conditions(rule), event):
        if is_dry_run:
            return {"matched": False, "status": "skipped", "reason": "conditions_not_met", "actions": [], "error": None}
        return _record(
            rule, event, "skipped", current_depth, {"reason": "conditions_not_met"}, None, started_at, db,
        )

    depth_token = None
    in_progress_token = None
    savepoint = None
    if not is_dry_run:
        depth_token = depth.set(current_depth + 1)
        in_progress_token = in_progress.set(in_progress.get() | frozenset({rule.id}))
    if is_dry_run:
        savepoint = db.begin_nested()

    actions_results: list[dict[str, Any]] = []
    failed = False
    try:
        for action in _load_actions(rule.id, db):
            handler = ACTION_REGISTRY.get(action.action_type)
            try:
                if handler is None:
                    raise ActionError(f"unknown action_type '{action.action_type}'")
                result = handler(_load_config(action), event, db)
                actions_results.append(
                    {
                        "action_type": action.action_type,
                        "position": action.position,
                        "ok": True,
                        "result": result,
                    }
                )
            except Exception as exc:  # noqa: BLE001 — record, never propagate
                failed = True
                actions_results.append(
                    {
                        "action_type": action.action_type,
                        "position": action.position,
                        "ok": False,
                        "error": str(exc),
                    }
                )
    finally:
        if savepoint is not None:
            savepoint.rollback()
        if in_progress_token is not None:
            in_progress.reset(in_progress_token)
        if depth_token is not None:
            depth.reset(depth_token)

    status = "failed" if failed else "success"

    if is_dry_run:
        return {
            "matched": True,
            "status": status,
            "reason": None,
            "actions": actions_results,
            "error": "one or more actions failed" if failed else None,
        }

    return _record(
        rule,
        event,
        status,
        current_depth,
        {"actions": actions_results},
        "one or more actions failed" if failed else None,
        started_at,
        db,
    )


def handle_event(event: BaseEvent, db: Session) -> None:
    """Process an event against every active rule of the event's organization.

    Subscribed to all event types; must never raise.
    """
    try:
        org_id = str(event.organization_id)
        rules = (
            db.query(AutomationRule)
            .filter(
                AutomationRule.organization_id == org_id,
                AutomationRule.is_active.is_(True),
                AutomationRule.trigger_event == event.event_type,
            )
            .order_by(AutomationRule.created_at.asc(), AutomationRule.id.asc())
            .all()
        )
        for rule in rules:
            try:
                _run_single(rule, event, db, is_dry_run=False)
            except Exception:  # noqa: BLE001
                log.exception("automation.rule_failed rule=%s event=%s", rule.id, event.event_type)
        db.flush()
    except Exception:  # noqa: BLE001
        log.exception("automation.engine_error event=%s", event.event_type)


def test_rule(rule_id: str, event: BaseEvent, db: Session, org_id: str) -> dict[str, Any]:
    """Dry-run a single rule against a synthetic event without persisting effects."""
    rule = (
        db.query(AutomationRule)
        .filter(AutomationRule.id == rule_id, AutomationRule.organization_id == org_id)
        .first()
    )
    if rule is None:
        raise NotFoundError(f"automation rule '{rule_id}' not found")

    token = dry_run.set(True)
    try:
        return _run_single(rule, event, db, is_dry_run=True)
    finally:
        dry_run.reset(token)
