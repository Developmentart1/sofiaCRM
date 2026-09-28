"""Pipelines module Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    description: str | None = None
    position: int = Field(ge=0)
    stage_type: str = Field(default="open", pattern=r"^(open|won|lost|discarded)$")
    probability: int = Field(ge=0, le=100)
    maximum_days: int | None = Field(default=None, ge=1)
    entry_requirements: str | None = None
    exit_requirements: str | None = None
    is_active: bool = True


class StageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    maximum_days: int | None = Field(default=None, ge=1)
    entry_requirements: str | None = None
    exit_requirements: str | None = None
    is_active: bool | None = None


class StageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    pipeline_id: UUID
    name: str
    description: str | None
    position: int
    stage_type: str
    probability: int
    maximum_days: int | None
    entry_requirements: str | None
    exit_requirements: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PipelineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    entity_type: str = Field(default="opportunity", pattern=r"^(opportunity|lead)$")
    is_default: bool = False
    is_active: bool = True
    stages: list[StageCreate] = Field(default_factory=list)


class PipelineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class PipelineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    entity_type: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PipelineWithStages(PipelineRead):
    stages: list[StageRead] = Field(default_factory=list)
