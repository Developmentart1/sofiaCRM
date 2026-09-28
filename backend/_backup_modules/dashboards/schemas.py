"""Dashboard Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KpiRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    open_count: int
    total_value: float
    weighted_value: float
    won_count: int
    lost_count: int
    overdue_tasks: int
    no_next_action: int
    stuck: int


class FunnelStage(BaseModel):
    stage_id: str
    stage_name: str
    count: int
    total_value: float
    weighted_value: float


class FunnelRead(BaseModel):
    stages: list[FunnelStage]
    total_open: int


class PerformanceRow(BaseModel):
    user_id: str
    user_name: str
    open_count: int
    won_count: int
    won_value: float
    weighted_value: float


class PerformanceRead(BaseModel):
    rows: list[PerformanceRow]


class SourceRow(BaseModel):
    source_id: str | None
    source_name: str
    count: int
    total_value: float


class SourcesRead(BaseModel):
    rows: list[SourceRow]
