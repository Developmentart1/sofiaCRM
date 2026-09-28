"""Opportunity Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LostReasonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    description: str | None = None
    is_active: bool = True


class LostReasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_active: bool


class LeadSourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    description: str | None = None
    is_active: bool = True


class LeadSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_active: bool


class OpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: UUID | None = None
    company_id: UUID | None = None
    pipeline_id: UUID
    stage_id: UUID
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    currency: str = Field(default="MXN", min_length=3, max_length=3)
    estimated_value: float = Field(default=0.0, ge=0.0)
    probability: int | None = Field(default=None, ge=0, le=100)
    priority: str = Field(default="normal", pattern=r"^(low|normal|high|urgent)$")
    status: str = Field(default="open", pattern=r"^(open|won|lost|discarded)$")
    source_id: UUID | None = None
    expected_close_date: datetime | None = None
    assigned_user_id: UUID | None = None
    team_id: str | None = Field(default=None, max_length=36)
    next_activity_at: datetime | None = None


class OpportunityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: UUID | None = None
    company_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    estimated_value: float | None = Field(default=None, ge=0.0)
    probability: int | None = Field(default=None, ge=0, le=100)
    priority: str | None = Field(default=None, pattern=r"^(low|normal|high|urgent)$")
    source_id: UUID | None = None
    expected_close_date: datetime | None = None
    assigned_user_id: UUID | None = None
    team_id: str | None = None
    next_activity_at: datetime | None = None


class OpportunityStageChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: UUID
    note: str | None = None


class OpportunityCloseLost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lost_reason_id: UUID
    lost_notes: str | None = None


class OpportunityCloseWon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    won_value: float | None = Field(default=None, ge=0.0)
    note: str | None = None


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    contact_id: UUID | None
    company_id: UUID | None
    pipeline_id: UUID
    stage_id: UUID
    name: str
    description: str | None
    currency: str
    estimated_value: float
    weighted_value: float
    probability: int
    priority: str
    status: str
    source_id: UUID | None
    expected_close_date: datetime | None
    closed_at: datetime | None
    won_value: float
    lost_reason_id: UUID | None
    lost_notes: str | None
    last_activity_at: datetime | None
    next_activity_at: datetime | None
    entered_stage_at: datetime
    assigned_user_id: UUID | None
    team_id: str | None
    is_stuck: bool
    created_at: datetime
    updated_at: datetime
