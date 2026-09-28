"""Dashboard KPI SQL — server-side aggregations, no Python loops over rows."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from core.tenant import current_org_id
from modules.activities.domain import Task
from modules.opportunities.domain import LeadSource, Opportunity
from modules.pipelines.domain import Stage
from modules.users.domain import User
from .schemas import (
    FunnelRead,
    FunnelStage,
    KpiRead,
    PerformanceRead,
    PerformanceRow,
    SourceRow,
    SourcesRead,
)


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def kpis(self) -> KpiRead:
        org = current_org_id()
        opp_q = (
            select(Opportunity)
            .where(Opportunity.organization_id == org, Opportunity.deleted_at.is_(None))
        )
        opp_all = list(self.db.execute(opp_q).scalars().all())

        def by_status(s: str) -> list[Opportunity]:
            return [o for o in opp_all if o.status == s]

        open_opps = by_status("open")
        won_opps = by_status("won")
        lost_opps = by_status("lost")

        total_value = sum(o.estimated_value for o in open_opps)
        weighted_value = sum(o.weighted_value for o in open_opps)

        stuck = sum(1 for o in open_opps if o.is_stuck)
        no_next_action = sum(1 for o in open_opps if not o.next_activity_at)

        overdue = self.db.execute(
            select(func.count(Task.id)).where(
                Task.organization_id == org,
                Task.status == "pending",
                Task.due_at.isnot(None),
                Task.due_at < datetime.now(UTC),
            )
        ).scalar_one() or 0

        return KpiRead(
            open_count=len(open_opps),
            total_value=round(total_value, 2),
            weighted_value=round(weighted_value, 2),
            won_count=len(won_opps),
            lost_count=len(lost_opps),
            overdue_tasks=int(overdue),
            no_next_action=no_next_action,
            stuck=stuck,
        )

    def funnel(self, pipeline_id: str | None = None) -> FunnelRead:
        org = current_org_id()
        # Stage-level aggregation
        stmt = (
            select(
                Stage.id.label("stage_id"),
                Stage.name.label("stage_name"),
                func.count(Opportunity.id).label("count"),
                func.coalesce(func.sum(Opportunity.estimated_value), 0.0).label("total_value"),
                func.coalesce(func.sum(Opportunity.weighted_value), 0.0).label("weighted_value"),
            )
            .select_from(Stage)
            .outerjoin(
                Opportunity,
                (Opportunity.stage_id == Stage.id)
                & (Opportunity.organization_id == org)
                & (Opportunity.deleted_at.is_(None))
                & (Opportunity.status == "open"),
            )
            .where(Stage.organization_id == org)
            .group_by(Stage.id, Stage.name, Stage.position)
            .order_by(Stage.position.asc())
        )
        if pipeline_id:
            stmt = stmt.where(Stage.pipeline_id == pipeline_id)
        rows = list(self.db.execute(stmt).all())
        stages = [
            FunnelStage(
                stage_id=str(r.stage_id),
                stage_name=r.stage_name,
                count=int(r.count or 0),
                total_value=float(r.total_value or 0.0),
                weighted_value=float(r.weighted_value or 0.0),
            )
            for r in rows
        ]
        total = sum(s.count for s in stages)
        return FunnelRead(stages=stages, total_open=total)

    def performance(self) -> PerformanceRead:
        org = current_org_id()
        stmt = (
            select(
                User.id.label("user_id"),
                User.full_name.label("user_name"),
                func.coalesce(
                    func.sum(case((Opportunity.status == "open", 1), else_=0)), 0
                ).label("open_count"),
                func.coalesce(
                    func.sum(case((Opportunity.status == "won", 1), else_=0)), 0
                ).label("won_count"),
                func.coalesce(func.sum(Opportunity.won_value), 0.0).label("won_value"),
                func.coalesce(func.sum(Opportunity.weighted_value), 0.0).label(
                    "weighted_value"
                ),
            )
            .select_from(User)
            .outerjoin(
                Opportunity,
                (Opportunity.assigned_user_id == User.id)
                & (Opportunity.organization_id == org)
                & (Opportunity.deleted_at.is_(None)),
            )
            .where(User.organization_id == org, User.is_active.is_(True))
            .group_by(User.id, User.full_name)
            .order_by(User.full_name.asc())
        )
        rows = list(self.db.execute(stmt).all())
        out = [
            PerformanceRow(
                user_id=str(r.user_id),
                user_name=r.user_name,
                open_count=int(r.open_count or 0),
                won_count=int(r.won_count or 0),
                won_value=float(r.won_value or 0.0),
                weighted_value=float(r.weighted_value or 0.0),
            )
            for r in rows
        ]
        return PerformanceRead(rows=out)

    def sources(self) -> SourcesRead:
        org = current_org_id()
        stmt = (
            select(
                LeadSource.id.label("source_id"),
                LeadSource.name.label("source_name"),
                func.count(Opportunity.id).label("count"),
                func.coalesce(func.sum(Opportunity.estimated_value), 0.0).label("total_value"),
            )
            .select_from(LeadSource)
            .outerjoin(
                Opportunity,
                (Opportunity.source_id == LeadSource.id)
                & (Opportunity.organization_id == org)
                & (Opportunity.deleted_at.is_(None)),
            )
            .where(LeadSource.organization_id == org)
            .group_by(LeadSource.id, LeadSource.name)
            .order_by(LeadSource.name.asc())
        )
        rows = list(self.db.execute(stmt).all())
        return SourcesRead(
            rows=[
                SourceRow(
                    source_id=str(r.source_id),
                    source_name=r.source_name,
                    count=int(r.count or 0),
                    total_value=float(r.total_value or 0.0),
                )
                for r in rows
            ]
        )
