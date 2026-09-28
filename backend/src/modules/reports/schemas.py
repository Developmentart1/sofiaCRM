"""Report Pydantic schemas — mirror the frontend ``DashboardKPIs``,
``ReportSummary`` and ``UserPerformance`` types exactly.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict


class DashboardKPIs(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_contacts: int
    total_companies: int
    total_opportunities: int
    open_opportunities_value: float
    won_opportunities_value: float
    won_opportunities_count: int
    lost_opportunities_count: int
    conversion_rate: float
    average_deal_size: float
    pipeline_velocity: float
    overdue_tasks: int
    tasks_due_today: int
    contacts_added_this_month: int
    opportunities_won_this_month: int


class RevenueByPipeline(BaseModel):
    pipeline_id: str
    pipeline_name: str
    revenue: float


class RevenueByOwner(BaseModel):
    user_id: str
    user_name: str
    revenue: float


class ConversionByStage(BaseModel):
    stage_id: str
    stage_name: str
    count: int
    conversion_rate: float


class ReportSummary(BaseModel):
    total_revenue: float
    revenue_by_pipeline: list[RevenueByPipeline]
    revenue_by_owner: list[RevenueByOwner]
    conversion_by_stage: list[ConversionByStage]
    period_start: date
    period_end: date


class UserPerformance(BaseModel):
    user_id: str
    user_name: str
    avatar_url: str | None = None
    opportunities_won: int
    opportunities_won_value: float
    opportunities_open: int
    activities_logged: int
    tasks_completed: int
