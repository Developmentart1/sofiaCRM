"""Opportunity service with business rules RB-001 to RB-018."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.errors import NotFoundError, StageTransitionError, ValidationError
from core.event_bus import (
    OpportunityCreated,
    OpportunityDiscarded,
    OpportunityLost,
    OpportunityStageChanged,
    OpportunityWon,
    get_bus,
)
from core.tenant import current_org_id
from .domain import Opportunity
from .schemas import OpportunityCreate, OpportunityUpdate, StageTransition


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_or_none(value: str | None) -> UUID | None:
    return UUID(value) if value else None


class OpportunityService:
    def __init__(self, db: Session):
        self.db = db

    # ── helpers ──────────────────────────────────────────

    def _get_stage(self, stage_id: str):
        """Fetch stage with org isolation. Returns sqlalchemy row."""
        org = current_org_id()
        from modules.pipelines.domain import Stage as StageModel
        s = self.db.query(StageModel).filter(
            StageModel.id == stage_id, StageModel.organization_id == org
        ).first()
        if not s:
            raise NotFoundError(f"stage {stage_id} not found")
        return s

    def _get_pipeline(self, pipeline_id: str):
        org = current_org_id()
        from modules.pipelines.domain import Pipeline as PipelineModel
        p = self.db.query(PipelineModel).filter(
            PipelineModel.id == pipeline_id, PipelineModel.organization_id == org
        ).first()
        if not p:
            raise NotFoundError(f"pipeline {pipeline_id} not found")
        return p

    # ── CRUD ─────────────────────────────────────────────

    def list_opportunities(self, status: str | None = None) -> list[Opportunity]:
        org = current_org_id()
        q = self.db.query(Opportunity).filter(
            Opportunity.organization_id == org, Opportunity.deleted_at.is_(None)
        )
        if status:
            q = q.filter(Opportunity.status == status)
        return q.order_by(Opportunity.created_at.desc()).all()

    def list_stuck_opportunities(self, *, days: int = 14) -> list[Opportunity]:
        """Open opportunities whose stage has not changed in ``days`` days.

        ``entered_stage_at`` is set whenever an opportunity is created or moved
        to a stage; ``created_at`` is the fallback for any legacy row with a
        NULL ``entered_stage_at``.
        """
        org = current_org_id()
        cutoff = _now() - timedelta(days=days)
        return (
            self.db.query(Opportunity)
            .filter(
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "open",
                func.coalesce(Opportunity.entered_stage_at, Opportunity.created_at) < cutoff,
            )
            .order_by(Opportunity.entered_stage_at.asc(), Opportunity.created_at.asc())
            .all()
        )

    def get_opportunity(self, opp_id: str) -> Opportunity:
        org = current_org_id()
        o = self.db.query(Opportunity).filter(
            Opportunity.id == opp_id, Opportunity.organization_id == org, Opportunity.deleted_at.is_(None)
        ).first()
        if not o:
            raise NotFoundError(f"opportunity {opp_id} not found")
        return o

    def create_opportunity(self, data: OpportunityCreate) -> Opportunity:
        org = current_org_id()
        stage = self._get_stage(data.stage_id)
        pipeline = self._get_pipeline(data.pipeline_id)

        # RB-004: stage must belong to pipeline
        if stage.pipeline_id != data.pipeline_id:
            raise ValidationError("stage does not belong to the selected pipeline")

        vals = data.model_dump()
        vals["organization_id"] = org
        vals["status"] = "open"
        vals["probability"] = stage.probability or 0
        vals["weighted_value"] = Decimal(str(vals.get("estimated_value", 0))) * vals["probability"] / 100
        vals["entered_stage_at"] = _now()

        o = Opportunity(**vals)
        self.db.add(o)
        self.db.flush()
        get_bus().publish(
            OpportunityCreated(
                organization_id=UUID(org),
                opportunity_id=UUID(o.id),
                title=o.name,
                pipeline_id=UUID(o.pipeline_id),
                stage_id=UUID(o.stage_id),
                value=float(o.estimated_value),
                currency=o.currency,
                assigned_user_id=_uuid_or_none(o.assigned_user_id),
            ),
            db=self.db,
        )
        self.db.commit()
        return o

    def update_opportunity(self, opp_id: str, data: OpportunityUpdate) -> Opportunity:
        o = self.get_opportunity(opp_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(o, k, v)
        # RB-010: recalculate weighted value if estimated_value or probability changed
        if data.estimated_value is not None or data.probability is not None:
            o.weighted_value = o.estimated_value * o.probability / 100
        o.updated_at = _now()
        self.db.commit()
        return o

    def transition_stage(self, opp_id: str, data: StageTransition) -> Opportunity:
        """Move opportunity to a new stage. Implements RB-005, RB-006, RB-007, RB-008."""
        org = current_org_id()
        o = self.get_opportunity(opp_id)
        if o.status != "open":
            raise StageTransitionError("only open opportunities can change stage")

        from_stage_id = o.stage_id
        stage = self._get_stage(data.stage_id)

        # RB-004: stage must belong to same pipeline
        if stage.pipeline_id != o.pipeline_id:
            raise StageTransitionError("stage does not belong to this opportunity's pipeline")

        # Detect close transitions
        if stage.stage_type == "won":
            # RB-006: record close date + final value
            o.status = "won"
            o.closed_at = _now()
            o.won_value = o.estimated_value
        elif stage.stage_type == "lost":
            # RB-005: require lost reason
            if not data.lost_reason_id:
                raise ValidationError("lost_reason_id is required when closing as lost")
            o.status = "lost"
            o.closed_at = _now()
            o.lost_reason_id = data.lost_reason_id
            o.lost_notes = data.lost_notes

        # RB-008: update stage tracking fields
        o.stage_id = stage.id
        o.entered_stage_at = _now()
        o.probability = stage.probability or 0
        o.weighted_value = o.estimated_value * o.probability / 100
        o.updated_at = _now()
        self.db.flush()

        bus = get_bus()
        bus.publish(
            OpportunityStageChanged(
                organization_id=UUID(org),
                opportunity_id=UUID(o.id),
                from_stage_id=_uuid_or_none(from_stage_id),
                to_stage_id=UUID(stage.id),
                entered_stage_at=o.entered_stage_at,
            ),
            db=self.db,
        )
        if o.status == "won":
            bus.publish(
                OpportunityWon(
                    organization_id=UUID(org),
                    opportunity_id=UUID(o.id),
                    final_value=float(o.won_value),
                    currency=o.currency,
                ),
                db=self.db,
            )
        elif o.status == "lost":
            bus.publish(
                OpportunityLost(
                    organization_id=UUID(org),
                    opportunity_id=UUID(o.id),
                    lost_reason=str(o.lost_reason_id or ""),
                ),
                db=self.db,
            )

        self.db.commit()
        return o

    def delete_opportunity(self, opp_id: str) -> None:
        org = current_org_id()
        o = self.get_opportunity(opp_id)
        o.deleted_at = _now()
        o.status = "discarded"
        self.db.flush()
        get_bus().publish(
            OpportunityDiscarded(
                organization_id=UUID(org),
                opportunity_id=UUID(o.id),
                discarded_reason="",
            ),
            db=self.db,
        )
        self.db.commit()
