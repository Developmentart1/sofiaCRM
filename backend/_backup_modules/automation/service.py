"""Automation service: create/list rules + receive plugin registration."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from core.event_bus import SyncEventBus
from .domain import AutomationRule
from .engine import AutomationEngine
from .repository import AutomationRepository
from .schemas import (
    AutomationExecutionRead,
    AutomationRuleCreate,
    AutomationRuleRead,
)


class AutomationService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = AutomationRepository(db)
        self.engine = AutomationEngine(db)

    def list_rules(self) -> list[AutomationRuleRead]:
        return [AutomationRuleRead.model_validate(r) for r in self.repo.list_rules()]

    def get_rule(self, rule_id: str) -> AutomationRuleRead:
        return AutomationRuleRead.model_validate(self.repo.get_rule(rule_id))

    def create_rule(self, payload: AutomationRuleCreate) -> AutomationRuleRead:
        rule = self.repo.create_rule(
            name=payload.name,
            description=payload.description,
            trigger_event_type=payload.trigger_event_type,
            is_active=payload.is_active,
        )
        for cond in payload.conditions:
            self.repo.add_condition(
                rule.id,
                field=cond.field,
                operator=cond.operator,
                value_json=json.dumps(cond.value),
            )
        for idx, act in enumerate(payload.actions):
            self.repo.add_action(
                rule.id,
                action_type=act.action_type,
                params=act.params,
                order=idx,
            )
        # Cycle prevention at registration time.
        self.engine.assert_no_self_trigger(rule, self.repo.list_actions(rule.id))
        return AutomationRuleRead.model_validate(rule)

    def last_executions(self, limit: int = 50) -> list[AutomationExecutionRead]:
        from .domain import AutomationExecution

        from core.tenant import current_org_id
        from sqlalchemy import desc, select

        org = current_org_id()
        stmt = (
            select(AutomationExecution)
            .where(AutomationExecution.organization_id == org)
            .order_by(desc(AutomationExecution.executed_at))
            .limit(limit)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return [AutomationExecutionRead.model_validate(r) for r in rows]
