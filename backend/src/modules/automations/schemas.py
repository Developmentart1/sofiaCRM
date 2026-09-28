"""Automation Pydantic schemas — rule CRUD, executions and dry-run requests."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .conditions import OPS


class ConditionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    op: str = "eq"
    value: str | int | float | bool | None = None

    @field_validator("op")
    @classmethod
    def _valid_op(cls, value: str) -> str:
        if value not in OPS:
            raise ValueError(f"op must be one of {sorted(OPS)}")
        return value


class ActionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: str
    config: dict[str, Any] = Field(default_factory=dict)


class RuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    trigger_event: str
    is_active: bool = True
    max_depth: int = Field(default=5, ge=1, le=100)
    conditions: list[ConditionSpec] = Field(default_factory=list)
    actions: list[ActionSpec] = Field(default_factory=list)


class RuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    trigger_event: str | None = None
    is_active: bool | None = None
    max_depth: int | None = Field(default=None, ge=1, le=100)
    conditions: list[ConditionSpec] | None = None
    actions: list[ActionSpec] | None = None


class ActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action_type: str
    config: dict[str, Any]
    position: int


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    trigger_event: str
    is_active: bool
    max_depth: int
    conditions: list[ConditionSpec] = Field(default_factory=list)
    actions: list[ActionRead] = Field(default_factory=list)
    execution_count: int = 0
    last_execution_status: str | None = None
    created_at: datetime
    updated_at: datetime


class ExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_id: str
    rule_name: str | None = None
    trigger_event_id: str
    status: str
    depth: int
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class RuleTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RuleTestActionResult(BaseModel):
    action_type: str
    position: int
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None


class RuleTestResult(BaseModel):
    matched: bool
    status: str
    reason: str | None = None
    actions: list[RuleTestActionResult] = Field(default_factory=list)
    error: str | None = None
