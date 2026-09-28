"""Pipeline schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    position: int = 0
    color: str | None = Field(default=None, max_length=9)
    probability: int = Field(default=0, ge=0, le=100)
    maximum_days: int | None = None
    stage_type: str = Field(default="open")
    entry_requirements: str | None = None
    exit_requirements: str | None = None


class StageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None = None
    position: int
    color: str | None = None
    probability: int
    maximum_days: int | None = None
    stage_type: str
    entry_requirements: str | None = None
    exit_requirements: str | None = None
    is_active: bool


class PipelineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class PipelineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    name: str
    description: str | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PipelineDetail(PipelineRead):
    stages: list[StageRead] = []
