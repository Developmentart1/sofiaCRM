"""Opportunity schemas."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class OpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contact_id: str | None = None
    company_id: str | None = None
    pipeline_id: str
    stage_id: str
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    currency: str = "MXN"
    estimated_value: float = Field(default=0, ge=0)
    priority: str = "medium"
    source_id: str | None = None
    expected_close_date: date | None = None
    assigned_user_id: str | None = None


class OpportunityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    priority: str | None = None
    source_id: str | None = None
    expected_close_date: date | None = None
    assigned_user_id: str | None = None
    probability: int | None = Field(default=None, ge=0, le=100)


class StageTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage_id: str
    lost_reason_id: str | None = None
    lost_notes: str | None = None


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    contact_id: str | None = None
    company_id: str | None = None
    pipeline_id: str
    stage_id: str
    name: str
    description: str | None = None
    currency: str
    estimated_value: float
    weighted_value: float
    probability: int
    priority: str
    status: str
    source_id: str | None = None
    expected_close_date: date | None = None
    closed_at: datetime | None = None
    won_value: float | None = None
    lost_reason_id: str | None = None
    lost_notes: str | None = None
    last_activity_at: datetime | None = None
    next_activity_at: datetime | None = None
    entered_stage_at: datetime | None = None
    assigned_user_id: str | None = None
    created_at: datetime
    updated_at: datetime
