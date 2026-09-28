"""Automation service — rule CRUD + execution history, all tenant-scoped."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.errors import NotFoundError, ValidationError
from core.pagination import PaginatedResponse
from core.tenant import current_org_id
from modules.pipelines.domain import Stage
from modules.users.domain import User
from .actions import ACTION_REGISTRY
from .domain import AutomationAction, AutomationExecution, AutomationRule
from .engine import all_event_types
from .schemas import (
    ActionRead,
    ConditionSpec,
    ExecutionRead,
    RuleCreate,
    RuleRead,
    RuleUpdate,
)


def _org_id() -> str:
    return current_org_id()


def _validate_trigger(trigger_event: str) -> None:
    if trigger_event not in all_event_types():
        raise ValidationError(
            f"unknown trigger_event '{trigger_event}'",
            details={"known": sorted(all_event_types())},
        )


def _validate_actions(actions: list[Any], org_id: str, db: Session) -> None:
    for action in actions:
        if action.action_type not in ACTION_REGISTRY:
            raise ValidationError(
                f"unknown action_type '{action.action_type}'",
                details={"known": sorted(ACTION_REGISTRY)},
            )
        config = action.config or {}
        if action.action_type == "move_stage":
            stage_id = config.get("stage_id")
            if not stage_id:
                raise ValidationError("move_stage requires config.stage_id")
            stage = (
                db.query(Stage)
                .filter(Stage.id == str(stage_id), Stage.organization_id == org_id)
                .first()
            )
            if stage is None:
                raise ValidationError(f"stage '{stage_id}' not found in organization")
        if action.action_type in ("create_task", "create_activity"):
            static_owner = config.get("assigned_user_id")
            if static_owner:
                user = (
                    db.query(User)
                    .filter(User.id == str(static_owner), User.organization_id == org_id)
                    .first()
                )
                if user is None:
                    raise ValidationError(f"assigned_user_id '{static_owner}' not found in organization")


class AutomationService:
    def __init__(self, db: Session):
        self.db = db

    # ── helpers ──────────────────────────────────────────

    def _get_rule_orm(self, rule_id: str) -> AutomationRule:
        org = _org_id()
        rule = (
            self.db.query(AutomationRule)
            .filter(AutomationRule.id == rule_id, AutomationRule.organization_id == org)
            .first()
        )
        if rule is None:
            raise NotFoundError(f"automation rule '{rule_id}' not found")
        return rule

    def _load_conditions(self, rule: AutomationRule) -> list[ConditionSpec]:
        if not rule.conditions_json:
            return []
        try:
            parsed = json.loads(rule.conditions_json)
        except (ValueError, TypeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [ConditionSpec(**c) for c in parsed if isinstance(c, dict)]

    def _load_actions(self, rule_id: str) -> list[ActionRead]:
        actions = (
            self.db.query(AutomationAction)
            .filter(AutomationAction.rule_id == rule_id)
            .order_by(AutomationAction.position.asc(), AutomationAction.id.asc())
            .all()
        )
        result: list[ActionRead] = []
        for a in actions:
            config = {}
            try:
                parsed = json.loads(a.config_json)
                if isinstance(parsed, dict):
                    config = parsed
            except (ValueError, TypeError):
                pass
            result.append(ActionRead(id=a.id, action_type=a.action_type, config=config, position=a.position))
        return result

    def _to_read(self, rule: AutomationRule) -> RuleRead:
        execution_count = (
            self.db.query(func.count(AutomationExecution.id))
            .filter(AutomationExecution.rule_id == rule.id)
            .scalar()
            ) or 0
        last = (
            self.db.query(AutomationExecution)
            .filter(AutomationExecution.rule_id == rule.id)
            .order_by(AutomationExecution.started_at.desc())
            .first()
        )
        return RuleRead(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            trigger_event=rule.trigger_event,
            is_active=rule.is_active,
            max_depth=rule.max_depth,
            conditions=self._load_conditions(rule),
            actions=self._load_actions(rule.id),
            execution_count=execution_count,
            last_execution_status=last.status if last else None,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )

    # ── rule CRUD ────────────────────────────────────────

    def list_rules(self) -> list[RuleRead]:
        org = _org_id()
        rules = (
            self.db.query(AutomationRule)
            .filter(AutomationRule.organization_id == org)
            .order_by(AutomationRule.created_at.asc(), AutomationRule.id.asc())
            .all()
        )
        return [self._to_read(r) for r in rules]

    def get_rule(self, rule_id: str) -> RuleRead:
        return self._to_read(self._get_rule_orm(rule_id))

    def _replace_actions(self, rule_id: str, actions: list[Any]) -> None:
        self.db.query(AutomationAction).filter(AutomationAction.rule_id == rule_id).delete()
        for position, action in enumerate(actions):
            self.db.add(
                AutomationAction(
                    rule_id=rule_id,
                    action_type=action.action_type,
                    config_json=json.dumps(action.config or {}),
                    position=position,
                )
            )

    def create_rule(self, data: RuleCreate) -> RuleRead:
        org = _org_id()
        _validate_trigger(data.trigger_event)
        _validate_actions(data.actions, org, self.db)

        rule = AutomationRule(
            organization_id=org,
            name=data.name,
            description=data.description,
            trigger_event=data.trigger_event,
            is_active=data.is_active,
            max_depth=data.max_depth,
            conditions_json=json.dumps([c.model_dump() for c in data.conditions]),
        )
        self.db.add(rule)
        self.db.flush()
        self._replace_actions(rule.id, data.actions)
        self.db.commit()
        return self._to_read(rule)

    def update_rule(self, rule_id: str, data: RuleUpdate) -> RuleRead:
        rule = self._get_rule_orm(rule_id)
        updates = data.model_dump(exclude_unset=True)

        if "trigger_event" in updates and updates["trigger_event"] is not None:
            _validate_trigger(updates["trigger_event"])
        if "actions" in updates and updates["actions"] is not None:
            _validate_actions(updates["actions"], _org_id(), self.db)

        for field in ("name", "description", "trigger_event", "is_active", "max_depth"):
            if field in updates and updates[field] is not None:
                setattr(rule, field, updates[field])
        if "conditions" in updates and updates["conditions"] is not None:
            rule.conditions_json = json.dumps([c.model_dump() for c in updates["conditions"]])
        if "actions" in updates and updates["actions"] is not None:
            self._replace_actions(rule.id, updates["actions"])

        self.db.commit()
        return self._to_read(rule)

    def delete_rule(self, rule_id: str) -> None:
        rule = self._get_rule_orm(rule_id)
        self.db.delete(rule)
        self.db.commit()

    # ── executions ──────────────────────────────────────

    def list_executions(
        self,
        *,
        rule_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ExecutionRead]:
        org = _org_id()
        q = (
            self.db.query(AutomationExecution, AutomationRule.name)
            .join(AutomationRule, AutomationRule.id == AutomationExecution.rule_id)
            .filter(AutomationRule.organization_id == org)
        )
        if rule_id:
            q = q.filter(AutomationExecution.rule_id == rule_id)
        if status:
            q = q.filter(AutomationExecution.status == status)

        total = q.count()
        rows = (
            q.order_by(AutomationExecution.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items: list[ExecutionRead] = []
        for exec_row, rule_name in rows:
            result = None
            if exec_row.result_json:
                try:
                    parsed = json.loads(exec_row.result_json)
                    if isinstance(parsed, dict):
                        result = parsed
                except (ValueError, TypeError):
                    pass
            items.append(
                ExecutionRead(
                    id=exec_row.id,
                    rule_id=exec_row.rule_id,
                    rule_name=rule_name,
                    trigger_event_id=exec_row.trigger_event_id,
                    status=exec_row.status,
                    depth=exec_row.depth,
                    result=result,
                    error=exec_row.error,
                    started_at=exec_row.started_at,
                    finished_at=exec_row.finished_at,
                )
            )
        return PaginatedResponse.of(items=items, total=total, page=page, page_size=page_size)
