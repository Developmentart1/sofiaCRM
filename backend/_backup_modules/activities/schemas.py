"""Activities + Tasks Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_type: str = Field(
        pattern=r"^(call|email|message|meeting|note|task|document|stage_change|status_change|payment|system)$"
    )
    subject: str = Field(min_length=2, max_length=200)
    description: str | None = None
    opportunity_id: UUID | None = None
    contact_id: UUID | None = None
    assigned_user_id: UUID | None = None
    occurred_at: datetime | None = None


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    activity_type: str
    subject: str
    description: str | None
    opportunity_id: UUID | None
    contact_id: UUID | None
    assigned_user_id: UUID | None
    performed_by: UUID | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    opportunity_id: UUID | None = None
    assigned_user_id: UUID | None = None
    priority: str = Field(default="normal", pattern=r"^(low|normal|high|urgent)$")
    due_at: datetime | None = None
    reminder_at: datetime | None = None


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    priority: str | None = Field(default=None, pattern=r"^(low|normal|high|urgent)$")
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    status: str | None = Field(default=None, pattern=r"^(pending|in_progress|completed|cancelled|overdue)$")


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    title: str
    description: str | None
    opportunity_id: UUID | None
    assigned_user_id: UUID | None
    created_by: UUID | None
    status: str
    priority: str
    due_at: datetime | None
    completed_at: datetime | None
    reminder_at: datetime | None
    is_overdue: bool
    created_at: datetime
    updated_at: datetime
