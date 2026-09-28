"""Automation Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AutomationConditionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=80)
    operator: str = Field(pattern=r"^(eq|ne|gt|lt|contains|in)$")
    value: object


class AutomationActionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: str = Field(
        pattern=r"^(create_task|assign_user|create_notification|update_field|add_tag|create_activity|send_internal_alert)$"
    )
    params: dict[str, object] = Field(default_factory=dict)


class AutomationRuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    trigger_event_type: str = Field(min_length=1, max_length=64)
    is_active: bool = True
    conditions: list[AutomationConditionSpec] = Field(default_factory=list)
    actions: list[AutomationActionSpec] = Field(default_factory=list)


class AutomationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    trigger_event_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AutomationExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    rule_id: UUID
    event_id: str
    executed_at: datetime
    status: str
    error: str | None
    depth: int
