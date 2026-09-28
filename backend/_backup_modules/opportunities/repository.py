"""Opportunity repository. Every read scoped by organization_id and deleted_at IS NULL."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import LostReason, LeadSource, Opportunity


class LostReasonRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, reason_id: str) -> LostReason:
        org = current_org_id()
        stmt = select(LostReason).where(LostReason.id == reason_id, LostReason.organization_id == org)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"lost_reason {reason_id} not found")
        return row

    def list_all(self) -> list[LostReason]:
        org = current_org_id()
        stmt = select(LostReason).where(LostReason.organization_id == org).order_by(LostReason.name.asc())
        return list(self.db.execute(stmt).scalars().all())

    def create(self, *, name: str, description: str | None, is_active: bool) -> LostReason:
        org = current_org_id()
        r = LostReason(organization_id=org, name=name, description=description, is_active=is_active)
        self.db.add(r)
        self.db.flush()
        return r


class LeadSourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, source_id: str) -> LeadSource:
        org = current_org_id()
        stmt = select(LeadSource).where(LeadSource.id == source_id, LeadSource.organization_id == org)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"lead_source {source_id} not found")
        return row

    def list_all(self) -> list[LeadSource]:
        org = current_org_id()
        stmt = select(LeadSource).where(LeadSource.organization_id == org).order_by(LeadSource.name.asc())
        return list(self.db.execute(stmt).scalars().all())

    def create(self, *, name: str, description: str | None, is_active: bool) -> LeadSource:
        org = current_org_id()
        s = LeadSource(organization_id=org, name=name, description=description, is_active=is_active)
        self.db.add(s)
        self.db.flush()
        return s


class OpportunityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, opp_id: str) -> Opportunity:
        org = current_org_id()
        stmt = select(Opportunity).where(
            Opportunity.id == opp_id,
            Opportunity.organization_id == org,
            Opportunity.deleted_at.is_(None),
        )
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"opportunity {opp_id} not found")
        return row

    def list_filtered(
        self,
        *,
        status: str | None = None,
        pipeline_id: str | None = None,
        stage_id: str | None = None,
        assigned_user_id: str | None = None,
        limit: int = 100,
    ) -> list[Opportunity]:
        org = current_org_id()
        stmt = select(Opportunity).where(
            Opportunity.organization_id == org,
            Opportunity.deleted_at.is_(None),
        )
        if status is not None:
            stmt = stmt.where(Opportunity.status == status)
        if pipeline_id is not None:
            stmt = stmt.where(Opportunity.pipeline_id == pipeline_id)
        if stage_id is not None:
            stmt = stmt.where(Opportunity.stage_id == stage_id)
        if assigned_user_id is not None:
            stmt = stmt.where(Opportunity.assigned_user_id == assigned_user_id)
        stmt = stmt.order_by(Opportunity.updated_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count_by_status(self, status: str) -> int:
        org = current_org_id()
        from sqlalchemy import func

        stmt = select(func.count(Opportunity.id)).where(
            Opportunity.organization_id == org,
            Opportunity.deleted_at.is_(None),
            Opportunity.status == status,
        )
        return int(self.db.execute(stmt).scalar_one() or 0)

    def sum_value_by_status(self, status: str, *, weighted: bool = False) -> float:
        org = current_org_id()
        from sqlalchemy import func

        col = Opportunity.weighted_value if weighted else Opportunity.estimated_value
        stmt = select(func.coalesce(func.sum(col), 0.0)).where(
            Opportunity.organization_id == org,
            Opportunity.deleted_at.is_(None),
            Opportunity.status == status,
        )
        return float(self.db.execute(stmt).scalar_one() or 0.0)

    def sum_won_value(self) -> float:
        org = current_org_id()
        from sqlalchemy import func

        stmt = select(func.coalesce(func.sum(Opportunity.won_value), 0.0)).where(
            Opportunity.organization_id == org,
            Opportunity.deleted_at.is_(None),
            Opportunity.status == "won",
        )
        return float(self.db.execute(stmt).scalar_one() or 0.0)
