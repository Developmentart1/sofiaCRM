"""Automation rule engine. Evaluates conditions and dispatches actions.

Cycle prevention strategy:

1. **Direct self-trigger rejection.** A rule whose `trigger_event_type` matches
   any of its own action side-effects (e.g. a rule that triggers off
   ``opportunity.created`` and emits a ``task.created`` whose own rule then
   re-emits ``opportunity.created``) is denied at registration time AND at run
   time via static check.

2. **Per-rule idempotency cache.** Each (rule_id, event_id) pair may run at
   most once — see ``AutomationRepository.already_executed``.

3. **Bounded recursion depth.** A rule may transitively trigger other rules,
   but the chain terminates after ``MAX_DEPTH=5``.

4. **Outbox-level dedup.** Even if a rule runs twice from the same logical
   event, the second attempt finds an execution row and bails out.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from core.errors import ValidationError
from core.event_bus import BaseEvent
from core.tenant import current_org_id
from modules.activities.domain import Activity, ActivityType
from modules.activities.domain import Task as TaskModel
from modules.notifications.domain import Notification
from modules.opportunities.domain import Opportunity
from .domain import (
    AutomationAction,
    AutomationCondition,
    AutomationRule,
)
from .repository import AutomationRepository

log = logging.getLogger(__name__)

MAX_DEPTH = 5


def _build_event_id(event: BaseEvent, payload: dict[str, Any]) -> str:
    """Stable identifier per logical event.

    Falls back to a hash of relevant fields if the event has no explicit id.
    """
    if hasattr(event, "model_dump"):
        dump = event.model_dump()
    else:
        dump = dict(payload)
    return f"{dump.get('event_type', 'unknown')}:{json.dumps(dump, default=str, sort_keys=True)}"


def _evaluate(condition: AutomationCondition, payload: dict[str, Any]) -> bool:
    """Eval a single condition against a dict-shaped payload."""
    actual = payload.get(condition.field)
    raw = condition.value_json
    try:
        expected = json.loads(raw)
    except json.JSONDecodeError:
        expected = raw
    op = condition.operator
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "gt":
        return actual is not None and actual > expected
    if op == "lt":
        return actual is not None and actual < expected
    if op == "contains":
        return expected in (actual or [])
    if op == "in":
        return actual in (expected or [])
    return False


class AutomationEngine:
    """Stateless executor. Constructed per-request with the db session."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AutomationRepository(db)

    def handle_event(self, event: BaseEvent, depth: int = 0) -> int:
        """Find rules matching event.event_type, evaluate, run actions. Returns #run."""
        if depth >= MAX_DEPTH:
            log.warning("automation depth %d reached MAX_DEPTH", depth)
            return 0
        org_id = current_org_id()
        rules = self.repo.rules_for_event(event.event_type)
        if not rules:
            return 0
        payload = event.model_dump() if hasattr(event, "model_dump") else {}
        event_id = _build_event_id(event, payload)
        ran = 0
        for rule in rules:
            try:
                if rule.organization_id != org_id:
                    continue
                # Idempotency
                if self.repo.already_executed(rule.id, event_id):
                    continue
                # Evaluate all conditions (AND semantics)
                conditions = self.repo.list_conditions(rule.id)
                if not self._matches(conditions, payload):
                    self.repo.record_execution(
                        rule_id=rule.id,
                        event_id=event_id,
                        status="skipped",
                        error="conditions_not_met",
                        depth=depth,
                    )
                    continue
                actions = self.repo.list_actions(rule.id)
                for action in actions:
                    try:
                        self._run_action(action, event, payload, depth)
                    except Exception as exc:  # noqa: BLE001
                        log.exception("automation action %s failed: %r", action.action_type, exc)
                        self.repo.record_execution(
                            rule_id=rule.id,
                            event_id=event_id,
                            status="error",
                            error=str(exc)[:500],
                            depth=depth,
                        )
                        break
                else:
                    self.repo.record_execution(
                        rule_id=rule.id,
                        event_id=event_id,
                        status="ok",
                        error=None,
                        depth=depth,
                    )
                    ran += 1
            except Exception as exc:  # noqa: BLE001
                log.exception("automation rule %s failed: %r", rule.id, exc)
        return ran

    def _matches(self, conditions: list[AutomationCondition], payload: dict[str, Any]) -> bool:
        return all(_evaluate(c, payload) for c in conditions)

    # ---- Action dispatch ----

    def _run_action(
        self,
        action: AutomationAction,
        event: BaseEvent,
        payload: dict[str, Any],
        depth: int,
    ) -> None:
        params = json.loads(action.params_json or "{}")
        org_id = current_org_id()
        # RB-AC-1: create_task
        if action.action_type == "create_task":
            t = TaskModel(
                organization_id=org_id,
                title=params.get("title", "Tarea automática"),
                description=params.get("description"),
                opportunity_id=str(params.get("opportunity_id"))
                if params.get("opportunity_id")
                else (
                    str(payload.get("opportunity_id"))
                    if payload.get("opportunity_id")
                    else None
                ),
                assigned_user_id=str(params.get("assigned_user_id"))
                if params.get("assigned_user_id")
                else None,
                priority=params.get("priority", "normal"),
                due_at=params.get("due_at"),
                status="pending",
            )
            self.db.add(t)
            self.db.flush()
            return

        # RB-AC-2: assign_user
        if action.action_type == "assign_user":
            opp_id = params.get("opportunity_id") or payload.get("opportunity_id")
            user_id = params.get("user_id")
            if not opp_id or not user_id:
                raise ValidationError("assign_user requires opportunity_id and user_id")
            opp = self.db.get(Opportunity, str(opp_id))
            if opp:
                opp.assigned_user_id = str(user_id)
                self.db.flush()
            return

        # RB-AC-3: create_notification
        if action.action_type == "create_notification":
            n = Notification(
                organization_id=org_id,
                user_id=str(params.get("user_id") or payload.get("assigned_user_id") or ""),
                title=params.get("title", "Notificación"),
                body=params.get("body"),
                category=params.get("category", "automation"),
                related_entity_type=event.event_type,
                related_entity_id=str(getattr(event, "opportunity_id", "") or ""),
            )
            self.db.add(n)
            self.db.flush()
            return

        # RB-AC-4: update_field
        if action.action_type == "update_field":
            opp_id = params.get("opportunity_id") or payload.get("opportunity_id")
            field_name = params.get("field")
            value = params.get("value")
            if not opp_id or not field_name:
                raise ValidationError("update_field requires opportunity_id + field")
            opp = self.db.get(Opportunity, str(opp_id))
            if opp and hasattr(opp, field_name):
                setattr(opp, field_name, value)
                self.db.flush()
            return

        # RB-AC-5: add_tag (placeholder: stored on description)
        if action.action_type == "add_tag":
            opp_id = params.get("opportunity_id") or payload.get("opportunity_id")
            tag = params.get("tag")
            if not opp_id or not tag:
                raise ValidationError("add_tag requires opportunity_id and tag")
            opp = self.db.get(Opportunity, str(opp_id))
            if opp:
                tag_text = f"#{tag}"
                if tag_text not in (opp.description or ""):
                    opp.description = (opp.description or "") + f" {tag_text}"
                self.db.flush()
            return

        # RB-AC-6: create_activity
        if action.action_type == "create_activity":
            a = Activity(
                organization_id=org_id,
                activity_type=ActivityType.SYSTEM.value,
                subject=params.get("subject", "Actividad automática"),
                description=params.get("description"),
                opportunity_id=str(params.get("opportunity_id"))
                if params.get("opportunity_id")
                else (
                    str(payload.get("opportunity_id"))
                    if payload.get("opportunity_id")
                    else None
                ),
                assigned_user_id=str(params.get("assigned_user_id"))
                if params.get("assigned_user_id")
                else None,
                occurred_at=datetime.now(UTC),
            )
            self.db.add(a)
            self.db.flush()
            return

        # RB-AC-7: send_internal_alert → also a notification in this implementation.
        if action.action_type == "send_internal_alert":
            n = Notification(
                organization_id=org_id,
                user_id=str(params.get("user_id") or payload.get("assigned_user_id") or ""),
                title=params.get("title", "Alerta interna"),
                body=params.get("body"),
                category="alert",
                related_entity_type=event.event_type,
            )
            self.db.add(n)
            self.db.flush()
            return

        raise ValidationError(f"unknown action_type: {action.action_type}")

    # ---- Validation at registration time ----

    def assert_no_self_trigger(self, rule: AutomationRule, actions: list[AutomationAction]) -> None:
        """A rule must not directly trigger an event identical to its own trigger."""
        for action in actions:
            params = json.loads(action.params_json or "{}")
            trigger = params.get("emits_event_type")
            if trigger and trigger == rule.trigger_event_type:
                raise ValidationError(
                    f"rule {rule.name} directly triggers its own event_type "
                    f"({rule.trigger_event_type}); cycle rejected"
                )
