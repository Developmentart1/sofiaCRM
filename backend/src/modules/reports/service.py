"""Reports service — read-only, tenant-scoped SQL aggregations.

Every metric is computed with SQLAlchemy ``func`` aggregates filtered by the
current organization (never loading whole tables into Python). Formulas are
documented inline and in ``docs/fase3-informe.md``:

- conversion_rate   = won / (won + lost), 0 when denominator is 0.
- average_deal_size = won value / won count, 0 when no won deals.
- pipeline_velocity = won revenue over the last 30 days / 30 (avg per day).
- "this month"      = current UTC calendar month.
"""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from core.tenant import current_org_id
from modules.activities.domain import Activity
from modules.contacts.domain import Company, Contact
from modules.opportunities.domain import Opportunity
from modules.pipelines.domain import Pipeline, Stage
from modules.tasks.domain import Task
from modules.users.domain import User
from .schemas import (
    ConversionByStage,
    DashboardKPIs,
    ReportSummary,
    RevenueByOwner,
    RevenueByPipeline,
    UserPerformance,
)

_COMPLETED_TASK_STATES = ("completed", "cancelled")
_VELOCITY_WINDOW_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _month_start() -> date:
    return _today().replace(day=1)


def _won_value_expr():
    return func.coalesce(Opportunity.won_value, Opportunity.estimated_value)


def _to_float(value) -> float:
    return float(value or 0)


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def _org(self) -> str:
        return current_org_id()

    # ── KPIs ─────────────────────────────────────────────

    def kpis(self) -> DashboardKPIs:
        org = self._org()
        today = _today()
        month_start = _month_start()

        total_contacts = (
            self.db.query(func.count(Contact.id))
            .filter(Contact.organization_id == org, Contact.deleted_at.is_(None))
            .scalar()
            or 0
        )
        total_companies = (
            self.db.query(func.count(Company.id))
            .filter(Company.organization_id == org, Company.deleted_at.is_(None))
            .scalar()
            or 0
        )
        total_opportunities = (
            self.db.query(func.count(Opportunity.id))
            .filter(Opportunity.organization_id == org, Opportunity.deleted_at.is_(None))
            .scalar()
            or 0
        )
        open_value = (
            self.db.query(func.coalesce(func.sum(Opportunity.estimated_value), 0))
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "open",
            )
            .scalar()
        )
        won_value = (
            self.db.query(func.coalesce(func.sum(_won_value_expr()), 0))
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "won",
            )
            .scalar()
        )
        won_count = (
            self.db.query(func.count(Opportunity.id))
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "won",
            )
            .scalar()
            or 0
        )
        lost_count = (
            self.db.query(func.count(Opportunity.id))
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "lost",
            )
            .scalar()
            or 0
        )

        conversion_rate = won_count / (won_count + lost_count) if (won_count + lost_count) else 0.0
        average_deal_size = _to_float(won_value) / won_count if won_count else 0.0

        velocity_window_start = _now() - timedelta(days=_VELOCITY_WINDOW_DAYS)
        won_last_window = (
            self.db.query(func.coalesce(func.sum(_won_value_expr()), 0))
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "won",
                Opportunity.closed_at >= velocity_window_start,
            )
            .scalar()
        )
        pipeline_velocity = _to_float(won_last_window) / _VELOCITY_WINDOW_DAYS

        overdue_tasks = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.organization_id == org,
                Task.status.notin_(_COMPLETED_TASK_STATES),
                Task.due_date.isnot(None),
                Task.due_date < today,
            )
            .scalar()
            or 0
        )
        tasks_due_today = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.organization_id == org,
                Task.status.notin_(_COMPLETED_TASK_STATES),
                Task.due_date == today,
            )
            .scalar()
            or 0
        )
        contacts_added_this_month = (
            self.db.query(func.count(Contact.id))
            .filter(
                Contact.organization_id == org,
                Contact.deleted_at.is_(None),
                Contact.created_at >= datetime.combine(month_start, time.min),
            )
            .scalar()
            or 0
        )
        opportunities_won_this_month = (
            self.db.query(func.count(Opportunity.id))
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "won",
                Opportunity.closed_at >= datetime.combine(month_start, time.min),
            )
            .scalar()
            or 0
        )

        return DashboardKPIs(
            total_contacts=total_contacts,
            total_companies=total_companies,
            total_opportunities=total_opportunities,
            open_opportunities_value=_to_float(open_value),
            won_opportunities_value=_to_float(won_value),
            won_opportunities_count=won_count,
            lost_opportunities_count=lost_count,
            conversion_rate=conversion_rate,
            average_deal_size=average_deal_size,
            pipeline_velocity=pipeline_velocity,
            overdue_tasks=overdue_tasks,
            tasks_due_today=tasks_due_today,
            contacts_added_this_month=contacts_added_this_month,
            opportunities_won_this_month=opportunities_won_this_month,
        )

    # ── Summary ──────────────────────────────────────────

    def summary(
        self,
        *,
        from_: date | None = None,
        to: date | None = None,
        pipeline_id: str | None = None,
    ) -> ReportSummary:
        org = self._org()
        today = _today()
        from_date = from_ or (today - timedelta(days=_VELOCITY_WINDOW_DAYS))
        to_date = to or today
        from_dt = datetime.combine(from_date, time.min)
        to_dt = datetime.combine(to_date, time.max)

        total_revenue = (
            self.db.query(func.coalesce(func.sum(_won_value_expr()), 0))
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "won",
                Opportunity.closed_at.isnot(None),
                Opportunity.closed_at >= from_dt,
                Opportunity.closed_at <= to_dt,
                *([Opportunity.pipeline_id == pipeline_id] if pipeline_id else []),
            )
            .scalar()
        )

        by_pipeline_rows = (
            self.db.query(Opportunity.pipeline_id, Pipeline.name, func.coalesce(func.sum(_won_value_expr()), 0))
            .join(Pipeline, Pipeline.id == Opportunity.pipeline_id)
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "won",
                Opportunity.closed_at.isnot(None),
                Opportunity.closed_at >= from_dt,
                Opportunity.closed_at <= to_dt,
                *([Opportunity.pipeline_id == pipeline_id] if pipeline_id else []),
            )
            .group_by(Opportunity.pipeline_id, Pipeline.name)
            .order_by(func.sum(_won_value_expr()).desc())
            .all()
        )
        revenue_by_pipeline = [
            RevenueByPipeline(
                pipeline_id=pid,
                pipeline_name=pname or "—",
                revenue=_to_float(rev),
            )
            for pid, pname, rev in by_pipeline_rows
        ]

        by_owner_rows = (
            self.db.query(Opportunity.assigned_user_id, User.full_name, func.coalesce(func.sum(_won_value_expr()), 0))
            .join(User, User.id == Opportunity.assigned_user_id)
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "won",
                Opportunity.closed_at.isnot(None),
                Opportunity.closed_at >= from_dt,
                Opportunity.closed_at <= to_dt,
                *([Opportunity.pipeline_id == pipeline_id] if pipeline_id else []),
            )
            .group_by(Opportunity.assigned_user_id, User.full_name)
            .order_by(func.sum(_won_value_expr()).desc())
            .all()
        )
        revenue_by_owner = [
            RevenueByOwner(user_id=uid or "", user_name=uname or "—", revenue=_to_float(rev))
            for uid, uname, rev in by_owner_rows
        ]

        stage_rows = (
            self.db.query(
                Opportunity.stage_id,
                Stage.name,
                func.count(Opportunity.id),
                func.coalesce(
                    func.sum(
                        case((Opportunity.status == "won", 1), else_=0)
                    ),
                    0,
                ),
            )
            .join(Stage, Stage.id == Opportunity.stage_id)
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status.in_(("open", "won")),
            )
            .group_by(Opportunity.stage_id, Stage.name)
            .all()
        )
        conversion_by_stage = [
            ConversionByStage(
                stage_id=sid,
                stage_name=sname or "—",
                count=count,
                conversion_rate=(won_in_stage / count) if count else 0.0,
            )
            for sid, sname, count, won_in_stage in stage_rows
        ]

        return ReportSummary(
            total_revenue=_to_float(total_revenue),
            revenue_by_pipeline=revenue_by_pipeline,
            revenue_by_owner=revenue_by_owner,
            conversion_by_stage=conversion_by_stage,
            period_start=from_date,
            period_end=to_date,
        )

    # ── Performance ──────────────────────────────────────

    def performance(self, *, from_: date | None = None, to: date | None = None) -> list[UserPerformance]:
        org = self._org()
        today = _today()
        from_date = from_ or (today - timedelta(days=_VELOCITY_WINDOW_DAYS))
        to_date = to or today
        from_dt = datetime.combine(from_date, time.min)
        to_dt = datetime.combine(to_date, time.max)

        users = (
            self.db.query(User)
            .filter(User.organization_id == org)
            .order_by(User.full_name.asc(), User.id.asc())
            .all()
        )

        won_rows = {
            uid: (count, value)
            for uid, count, value in self.db.query(
                Opportunity.assigned_user_id,
                func.count(Opportunity.id),
                func.coalesce(func.sum(_won_value_expr()), 0),
            )
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "won",
                Opportunity.closed_at.isnot(None),
                Opportunity.closed_at >= from_dt,
                Opportunity.closed_at <= to_dt,
            )
            .group_by(Opportunity.assigned_user_id)
            .all()
        }
        open_rows = dict(
            self.db.query(Opportunity.assigned_user_id, func.count(Opportunity.id))
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "open",
            )
            .group_by(Opportunity.assigned_user_id)
            .all()
        )
        activity_rows = dict(
            self.db.query(Activity.user_id, func.count(Activity.id))
            .filter(
                Activity.organization_id == org,
                Activity.occurred_at.isnot(None),
                Activity.occurred_at >= from_dt,
                Activity.occurred_at <= to_dt,
            )
            .group_by(Activity.user_id)
            .all()
        )
        task_rows = dict(
            self.db.query(Task.assigned_user_id, func.count(Task.id))
            .filter(
                Task.organization_id == org,
                Task.status == "completed",
                Task.completed_at.isnot(None),
                Task.completed_at >= from_dt,
                Task.completed_at <= to_dt,
            )
            .group_by(Task.assigned_user_id)
            .all()
        )

        result: list[UserPerformance] = []
        for u in users:
            won_count, won_value = won_rows.get(u.id, (0, 0))
            result.append(
                UserPerformance(
                    user_id=u.id,
                    user_name=u.full_name,
                    avatar_url=u.avatar_url,
                    opportunities_won=int(won_count or 0),
                    opportunities_won_value=_to_float(won_value),
                    opportunities_open=int(open_rows.get(u.id, 0) or 0),
                    activities_logged=int(activity_rows.get(u.id, 0) or 0),
                    tasks_completed=int(task_rows.get(u.id, 0) or 0),
                )
            )
        return result

    # ── Pipeline Trend ─────────────────────────────────────────

    def pipeline_trend(self, days: int = 7) -> list[dict]:
        """Open pipeline value at the close of each of the last N days.

        Cumulative (running total), not per-day increments: per-day created
        value is 0 on any day without new deals, which makes the chart a flat
        line. Cumulative answers "how big is the open pipeline today".
        """
        org = self._org()
        today = _today()
        start_date = today - timedelta(days=days - 1)

        rows = (
            self.db.query(Opportunity.created_at, _won_value_expr())
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "open",
                Opportunity.created_at <= datetime.combine(today, time.max, tzinfo=timezone.utc),
            )
            .all()
        )

        result = []
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            # Both sides must be tz-aware: PostgreSQL/seeded rows return aware
            # created_at while SQLite returns naive (ORM-created rows), and
            # mixing them raises TypeError. Normalize created to UTC.
            cutoff = datetime.combine(current_date, time.max).replace(tzinfo=timezone.utc)
            total = sum(
                float(value or 0)
                for created, value in rows
                if (created if created.tzinfo else created.replace(tzinfo=timezone.utc)) <= cutoff
            )
            result.append({"date": current_date.isoformat(), "value": total})

        return result

    # ── Pipeline Distribution ──────────────────────────────────

    def pipeline_distribution(self) -> list[dict]:
        """Opportunity count per pipeline stage, every active stage included.

        OUTER join from Stage: an inner join silently drops empty stages, so a
        board with one populated column renders as a one-bar chart.
        """
        org = self._org()

        stage_counts = (
            self.db.query(
                Stage.name.label("stage_name"),
                func.count(Opportunity.id).label("count"),
            )
            .outerjoin(
                Opportunity,
                and_(
                    Opportunity.stage_id == Stage.id,
                    Opportunity.organization_id == org,
                    Opportunity.deleted_at.is_(None),
                ),
            )
            .filter(Stage.organization_id == org, Stage.is_active.is_(True))
            .group_by(Stage.id, Stage.name, Stage.position)
            .order_by(Stage.position)
            .all()
        )

        return [{"stage_name": s.stage_name or "—", "count": s.count or 0} for s in stage_counts]
