"""Automation repository — scoped by organization."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import (
    AutomationAction,
    AutomationCondition,
    AutomationExecution,
    AutomationRule,
)


class AutomationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_rule(
        self,
        *,
        name: str,
        description: str | None,
        trigger_event_type: str,
        is_active: bool,
    ) -> AutomationRule:
        org = current_org_id()
        r = AutomationRule(
            organization_id=org,
            name=name,
            description=description,
            trigger_event_type=trigger_event_type,
            is_active=is_active,
        )
        self.db.add(r)
        self.db.flush()
        return r

    def get_rule(self, rule_id: str) -> AutomationRule:
        org = current_org_id()
        stmt = select(AutomationRule).where(
            AutomationRule.id == rule_id, AutomationRule.organization_id == org
        )
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"automation rule {rule_id} not found")
        return row

    def list_rules(self) -> list[AutomationRule]:
        org = current_org_id()
        stmt = (
            select(AutomationRule)
            .where(AutomationRule.organization_id == org)
            .order_by(AutomationRule.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def rules_for_event(self, event_type: str) -> list[AutomationRule]:
        org = current_org_id()
        stmt = select(AutomationRule).where(
            AutomationRule.organization_id == org,
            AutomationRule.trigger_event_type == event_type,
            AutomationRule.is_active.is_(True),
        )
        return list(self.db.execute(stmt).scalars().all())

    def add_condition(self, rule_id: str, *, field: str, operator: str, value_json: str) -> AutomationCondition:
        org = current_org_id()
        c = AutomationCondition(
            organization_id=org,
            rule_id=rule_id,
            field=field,
            operator=operator,
            value_json=value_json,
        )
        self.db.add(c)
        self.db.flush()
        return c

    def list_conditions(self, rule_id: str) -> list[AutomationCondition]:
        stmt = select(AutomationCondition).where(AutomationCondition.rule_id == rule_id)
        return list(self.db.execute(stmt).scalars().all())

    def add_action(
        self, rule_id: str, *, action_type: str, params: dict[str, object], order: int
    ) -> AutomationAction:
        org = current_org_id()
        a = AutomationAction(
            organization_id=org,
            rule_id=rule_id,
            action_type=action_type,
            params_json=json.dumps(params),
            order=order,
        )
        self.db.add(a)
        self.db.flush()
        return a

    def list_actions(self, rule_id: str) -> list[AutomationAction]:
        stmt = (
            select(AutomationAction)
            .where(AutomationAction.rule_id == rule_id)
            .order_by(AutomationAction.order.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def already_executed(self, rule_id: str, event_id: str) -> bool:
        stmt = select(AutomationExecution.id).where(
            AutomationExecution.rule_id == rule_id, AutomationExecution.event_id == event_id
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def record_execution(
        self,
        *,
        rule_id: str,
        event_id: str,
        status: str,
        error: str | None,
        depth: int,
    ) -> AutomationExecution:
        org = current_org_id()
        e = AutomationExecution(
            organization_id=org,
            rule_id=rule_id,
            event_id=event_id,
            status=status,
            error=error,
            depth=depth,
        )
        self.db.add(e)
        self.db.flush()
        return e
