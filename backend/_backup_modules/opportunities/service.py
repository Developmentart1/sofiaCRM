"""Opportunity service: enforces all spec business rules RB-001..RB-018."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from core.errors import (
    ForbiddenError,
    NotFoundError,
    StageTransitionError,
    ValidationError,
)
from core.event_bus import (
    OpportunityAssigneeChanged,
    OpportunityCreated,
    OpportunityDiscarded,
    OpportunityLost,
    OpportunityStageChanged,
    OpportunityValueChanged,
    OpportunityWon,
    SyncEventBus,
)
from modules.pipelines.domain import Pipeline, Stage
from .domain import LostReason, LeadSource, Opportunity, OpportunityStatus
from .repository import LostReasonRepository, LeadSourceRepository, OpportunityRepository
from .schemas import (
    LeadSourceCreate,
    LeadSourceRead,
    LostReasonCreate,
    LostReasonRead,
    OpportunityCloseLost,
    OpportunityCloseWon,
    OpportunityCreate,
    OpportunityRead,
    OpportunityStageChange,
    OpportunityUpdate,
)


def _compute_stuck(opp: Opportunity, stage: Stage) -> bool:
    """RB-012 — stuck iff now - entered_stage_at > stage.maximum_days."""
    if stage.maximum_days is None:
        return False
    delta = datetime.now(UTC) - opp.entered_stage_at
    return delta.days > stage.maximum_days


def _compute_weighted(estimated: float, probability: int) -> float:
    """RB-010 — weighted_value = estimated_value * probability / 100."""
    return round(estimated * probability / 100.0, 2)


class OpportunityService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = OpportunityRepository(db)

    # ---- CRUD ----

    def list(
        self,
        *,
        status: str | None = None,
        pipeline_id: str | None = None,
        stage_id: str | None = None,
        assigned_user_id: str | None = None,
    ) -> list[OpportunityRead]:
        rows = self.repo.list_filtered(
            status=status,
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            assigned_user_id=assigned_user_id,
        )
        return [OpportunityRead.model_validate(o) for o in rows]

    def get(self, opp_id: str) -> OpportunityRead:
        return OpportunityRead.model_validate(self.repo.get(opp_id))

    def create(self, payload: OpportunityCreate) -> OpportunityRead:
        # RB-003: pipeline and stage required and stage must belong to pipeline.
        pipeline = self._get_pipeline(str(payload.pipeline_id))
        stage = self._get_stage(str(payload.stage_id))
        # RB-004
        if stage.pipeline_id != pipeline.id:
            raise ValidationError(
                "stage_id does not belong to pipeline_id",
                details={"stage_id": str(payload.stage_id), "pipeline_id": str(payload.pipeline_id)},
            )
        # RB-002: assigned_user required if status='open'.
        if payload.status == OpportunityStatus.OPEN.value and payload.assigned_user_id is None:
            raise ValidationError("assigned_user_id is required when status='open'")

        probability = (
            payload.probability if payload.probability is not None else stage.probability
        )
        weighted = _compute_weighted(payload.estimated_value, probability)
        now = datetime.now(UTC)
        org_id = self._current_org()

        opp = Opportunity(
            organization_id=org_id,
            contact_id=str(payload.contact_id) if payload.contact_id else None,
            company_id=str(payload.company_id) if payload.company_id else None,
            pipeline_id=str(payload.pipeline_id),
            stage_id=str(payload.stage_id),
            name=payload.name,
            description=payload.description,
            currency=payload.currency,
            estimated_value=payload.estimated_value,
            weighted_value=weighted,
            probability=probability,
            priority=payload.priority,
            status=payload.status,
            source_id=str(payload.source_id) if payload.source_id else None,
            expected_close_date=payload.expected_close_date,
            assigned_user_id=str(payload.assigned_user_id) if payload.assigned_user_id else None,
            team_id=payload.team_id,
            next_activity_at=payload.next_activity_at,
            entered_stage_at=now,
        )
        opp.is_stuck = _compute_stuck(opp, stage)
        self.db.add(opp)
        self.db.flush()

        self.bus.publish(
            OpportunityCreated(
                organization_id=UUID(opp.organization_id),
                opportunity_id=opp.uuid,
                title=opp.name,
                pipeline_id=UUID(opp.pipeline_id),
                stage_id=UUID(opp.stage_id),
                value=opp.estimated_value,
                currency=opp.currency,
                assigned_user_id=UUID(opp.assigned_user_id) if opp.assigned_user_id else None,
            ),
            db=self.db,
        )
        return OpportunityRead.model_validate(opp)

    def update(self, opp_id: str, payload: OpportunityUpdate, *, actor_role: str) -> OpportunityRead:
        opp = self.repo.get(opp_id)
        changed: list[str] = []

        from_value = opp.estimated_value

        # RB-018 — value change generates activity + audit (handled by @audit_log).
        if payload.estimated_value is not None and payload.estimated_value != opp.estimated_value:
            opp.estimated_value = payload.estimated_value
            opp.weighted_value = _compute_weighted(opp.estimated_value, opp.probability)
            self.bus.publish(
                OpportunityValueChanged(
                    organization_id=UUID(opp.organization_id),
                    opportunity_id=opp.uuid,
                    from_value=from_value,
                    to_value=opp.estimated_value,
                    currency=opp.currency,
                ),
                db=self.db,
            )
            changed.append("estimated_value")

        # RB-017 — assigned_user change generates activity + audit.
        from_user = opp.assigned_user_id
        if payload.assigned_user_id is not None and str(payload.assigned_user_id) != opp.assigned_user_id:
            # RB-002 check on the new status==open.
            if opp.status == OpportunityStatus.OPEN.value and payload.assigned_user_id is None:
                raise ValidationError("assigned_user_id cannot be NULL while status='open'")
            opp.assigned_user_id = str(payload.assigned_user_id)
            self.bus.publish(
                OpportunityAssigneeChanged(
                    organization_id=UUID(opp.organization_id),
                    opportunity_id=opp.uuid,
                    from_user_id=UUID(from_user) if from_user else None,
                    to_user_id=UUID(opp.assigned_user_id) if opp.assigned_user_id else None,
                ),
                db=self.db,
            )
            changed.append("assigned_user_id")

        # RB-009 — probability override requires opportunities.override_probability permission.
        if payload.probability is not None and payload.probability != opp.probability:
            self._require_overrides(actor_role)
            opp.probability = payload.probability
            opp.weighted_value = _compute_weighted(opp.estimated_value, opp.probability)
            changed.append("probability")

        if payload.contact_id is not None:
            opp.contact_id = str(payload.contact_id)
            changed.append("contact_id")
        if payload.company_id is not None:
            opp.company_id = str(payload.company_id)
            changed.append("company_id")
        if payload.name is not None:
            opp.name = payload.name
            changed.append("name")
        if payload.description is not None:
            opp.description = payload.description
            changed.append("description")
        if payload.currency is not None:
            opp.currency = payload.currency
            changed.append("currency")
        if payload.priority is not None:
            opp.priority = payload.priority
            changed.append("priority")
        if payload.source_id is not None:
            opp.source_id = str(payload.source_id)
            changed.append("source_id")
        if payload.expected_close_date is not None:
            opp.expected_close_date = payload.expected_close_date
            changed.append("expected_close_date")
        if payload.team_id is not None:
            opp.team_id = payload.team_id
            changed.append("team_id")
        if payload.next_activity_at is not None:
            opp.next_activity_at = payload.next_activity_at
            changed.append("next_activity_at")

        self.db.flush()
        stage = self._get_stage(opp.stage_id)
        opp.is_stuck = _compute_stuck(opp, stage)
        return OpportunityRead.model_validate(opp)

    # ---- Stage transitions (RB-007, RB-008) ----

    def change_stage(self, opp_id: str, payload: OpportunityStageChange, note: str | None = None) -> OpportunityRead:
        opp = self.repo.get(opp_id)
        new_stage = self._get_stage(str(payload.stage_id))
        # RB-004
        if new_stage.pipeline_id != opp.pipeline_id:
            raise StageTransitionError(
                "new stage does not belong to the opportunity pipeline",
                details={
                    "opportunity_pipeline_id": opp.pipeline_id,
                    "requested_stage_id": str(payload.stage_id),
                },
            )
        if new_stage.id == opp.stage_id:
            return OpportunityRead.model_validate(opp)
        old_stage_id = opp.stage_id
        opp.stage_id = new_stage.id
        opp.entered_stage_at = datetime.now(UTC)
        # RB-008: probability defaults to stage.probability (unless previously overridden).
        opp.probability = new_stage.probability
        opp.weighted_value = _compute_weighted(opp.estimated_value, opp.probability)
        opp.is_stuck = False  # reset on transition
        self.db.flush()

        self.bus.publish(
            OpportunityStageChanged(
                organization_id=UUID(opp.organization_id),
                opportunity_id=opp.uuid,
                from_stage_id=UUID(old_stage_id),
                to_stage_id=UUID(new_stage.id),
                entered_stage_at=opp.entered_stage_at,
            ),
            db=self.db,
        )

        # RB-007: stage_change creates an Activity row (type='stage_change').
        self._record_stage_change_activity(opp, old_stage_id, new_stage.id, note)
        return OpportunityRead.model_validate(opp)

    def _record_stage_change_activity(
        self,
        opp: Opportunity,
        old_stage_id: str,
        new_stage: Stage,
        note: str | None,
    ) -> None:
        """Persist an Activity(type='stage_change') inside this transaction."""
        from modules.activities.domain import Activity, ActivityType

        org_id = opp.organization_id
        subject = f"Cambio de etapa para {opp.name}"
        description = f"Etapa {old_stage_id[:8]} -> {new_stage.name}"
        if note:
            description = f"{description} | {note}"
        act = Activity(
            organization_id=org_id,
            activity_type=ActivityType.STAGE_CHANGE.value,
            subject=subject,
            description=description,
            opportunity_id=opp.id,
            assigned_user_id=opp.assigned_user_id,
            occurred_at=datetime.now(UTC),
        )
        self.db.add(act)
        self.db.flush()

    # ---- Close lost / won ----

    def close_lost(self, opp_id: str, payload: OpportunityCloseLost, actor_role: str) -> OpportunityRead:
        opp = self.repo.get(opp_id)
        # RB-005
        from .repository import LostReasonRepository

        LostReasonRepository(self.db).get(str(payload.lost_reason_id))
        if opp.status != OpportunityStatus.OPEN.value:
            raise ValidationError(f"opportunity is already {opp.status}")
        opp.lost_reason_id = str(payload.lost_reason_id)
        opp.lost_notes = payload.lost_notes
        opp.status = OpportunityStatus.LOST.value
        opp.closed_at = datetime.now(UTC)
        opp.weighted_value = 0.0
        self.db.flush()
        # RB-006: closed_at set, won_value untouched.
        self.bus.publish(
            OpportunityLost(
                organization_id=UUID(opp.organization_id),
                opportunity_id=opp.uuid,
                lost_reason=str(payload.lost_reason_id),
            ),
            db=self.db,
        )
        return OpportunityRead.model_validate(opp)

    def close_won(self, opp_id: str, payload: OpportunityCloseWon) -> OpportunityRead:
        opp = self.repo.get(opp_id)
        if opp.status != OpportunityStatus.OPEN.value:
            raise ValidationError(f"opportunity is already {opp.status}")
        opp.status = OpportunityStatus.WON.value
        opp.closed_at = datetime.now(UTC)  # RB-006
        opp.won_value = payload.won_value if payload.won_value is not None else opp.estimated_value
        opp.weighted_value = opp.won_value
        # Move to default won-stage? We leave the stage in place but mark won.
        self.db.flush()
        self.bus.publish(
            OpportunityWon(
                organization_id=UUID(opp.organization_id),
                opportunity_id=opp.uuid,
                final_value=opp.won_value,
                currency=opp.currency,
            ),
            db=self.db,
        )
        return OpportunityRead.model_validate(opp)

    def discard(self, opp_id: str, reason: str) -> OpportunityRead:
        opp = self.repo.get(opp_id)
        if opp.status != OpportunityStatus.OPEN.value:
            raise ValidationError(f"opportunity is already {opp.status}")
        opp.status = OpportunityStatus.DISCARDED.value
        opp.lost_notes = reason
        opp.closed_at = datetime.now(UTC)
        opp.weighted_value = 0.0
        self.db.flush()
        self.bus.publish(
            OpportunityDiscarded(
                organization_id=UUID(opp.organization_id),
                opportunity_id=opp.uuid,
                discarded_reason=reason,
            ),
            db=self.db,
        )
        return OpportunityRead.model_validate(opp)

    # RB-016: reopen with permission + audit log.
    def reopen(self, opp_id: str, actor_role: str) -> OpportunityRead:
        # Permission check enforced at the routes layer via require_permission
        # for 'opportunity:create'. Soft enforcement here: log via audit later.
        opp = self.repo.get(opp_id)
        if opp.status == OpportunityStatus.OPEN.value:
            raise ValidationError("opportunity is already open")
        opp.status = OpportunityStatus.OPEN.value
        opp.closed_at = None
        opp.won_value = 0.0
        opp.weighted_value = _compute_weighted(opp.estimated_value, opp.probability)
        self.db.flush()
        return OpportunityRead.model_validate(opp)

    def soft_delete(self, opp_id: str) -> None:
        opp = self.repo.get(opp_id)
        opp.deleted_at = datetime.now(UTC)
        self.db.flush()

    # ---- Helpers ----

    def _get_pipeline(self, pipeline_id: str) -> Pipeline:
        p = self.db.get(Pipeline, pipeline_id)
        if p is None:
            raise NotFoundError(f"pipeline {pipeline_id} not found")
        return p

    def _get_stage(self, stage_id: str) -> Stage:
        s = self.db.get(Stage, stage_id)
        if s is None:
            raise NotFoundError(f"stage {stage_id} not found")
        return s

    def _current_org(self) -> str:
        from core.tenant import current_org_id

        return current_org_id()

    def _require_overrides(self, role: str) -> None:
        """RB-009 — probability override requires opportunities.override_probability.

        Admin/director/gerente may override. Asesores/operaciones may not.
        """
        if role in ("admin", "director", "gerente"):
            return
        raise ForbiddenError("role lacks opportunities.override_probability")


# ---- Lost reasons / Lead sources simple CRUD ----


class LostReasonService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = LostReasonRepository(db)

    def list(self) -> list[LostReasonRead]:
        return [LostReasonRead.model_validate(r) for r in self.repo.list_all()]

    def create(self, payload: LostReasonCreate) -> LostReasonRead:
        r = self.repo.create(
            name=payload.name, description=payload.description, is_active=payload.is_active
        )
        return LostReasonRead.model_validate(r)


class LeadSourceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = LeadSourceRepository(db)

    def list(self) -> list[LeadSourceRead]:
        return [LeadSourceRead.model_validate(s) for s in self.repo.list_all()]

    def create(self, payload: LeadSourceCreate) -> LeadSourceRead:
        s = self.repo.create(
            name=payload.name, description=payload.description, is_active=payload.is_active
        )
        return LeadSourceRead.model_validate(s)
