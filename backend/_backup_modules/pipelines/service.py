"""Pipelines module: business orchestration around stages."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from core.errors import ValidationError
from core.event_bus import PipelineCreated, StageCreated, SyncEventBus
from .domain import Pipeline, Stage
from .repository import PipelineRepository, StageRepository
from .schemas import (
    PipelineCreate,
    PipelineRead,
    PipelineUpdate,
    PipelineWithStages,
    StageCreate,
    StageRead,
    StageUpdate,
)


class PipelineService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = PipelineRepository(db)
        self.stages_repo = StageRepository(db)

    def list(self) -> list[PipelineRead]:
        return [PipelineRead.model_validate(p) for p in self.repo.list_all()]

    def get(self, pipeline_id: str) -> PipelineWithStages:
        p = self.repo.get(pipeline_id)
        stages = self.stages_repo.list_by_pipeline(pipeline_id)
        out = PipelineWithStages.model_validate(p)
        out.stages = [StageRead.model_validate(s) for s in stages]
        return out

    def create(self, payload: PipelineCreate) -> PipelineWithStages:
        p = self.repo.create(
            name=payload.name,
            description=payload.description,
            entity_type=payload.entity_type,
            is_default=payload.is_default,
            is_active=payload.is_active,
        )
        stages: list[Stage] = []
        for st in payload.stages:
            stages.append(
                self.stages_repo.create(
                    pipeline_id=p.id,
                    name=st.name,
                    description=st.description,
                    position=st.position,
                    stage_type=st.stage_type,
                    probability=st.probability,
                    maximum_days=st.maximum_days,
                    entry_requirements=st.entry_requirements,
                    exit_requirements=st.exit_requirements,
                    is_active=st.is_active,
                )
            )
        self.bus.publish(
            PipelineCreated(organization_id=UUID(p.organization_id), pipeline_id=UUID(p.id), name=p.name),
            db=self.db,
        )
        for s in stages:
            self.bus.publish(
                StageCreated(
                    organization_id=UUID(s.organization_id),
                    stage_id=UUID(s.id),
                    pipeline_id=UUID(s.pipeline_id),
                    name=s.name,
                ),
                db=self.db,
            )
        out = PipelineWithStages.model_validate(p)
        out.stages = [StageRead.model_validate(s) for s in stages]
        return out

    def update(self, pipeline_id: str, payload: PipelineUpdate) -> PipelineRead:
        p = self.repo.get(pipeline_id)
        self.repo.update(
            p,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
            is_active=payload.is_active,
        )
        return PipelineRead.model_validate(p)

    def add_stage(self, pipeline_id: str, payload: StageCreate) -> StageRead:
        self.repo.get(pipeline_id)  # validate exists
        s = self.stages_repo.create(
            pipeline_id=pipeline_id,
            name=payload.name,
            description=payload.description,
            position=payload.position,
            stage_type=payload.stage_type,
            probability=payload.probability,
            maximum_days=payload.maximum_days,
            entry_requirements=payload.entry_requirements,
            exit_requirements=payload.exit_requirements,
            is_active=payload.is_active,
        )
        if payload.probability < 0 or payload.probability > 100:
            raise ValidationError("probability must be between 0 and 100")
        self.bus.publish(
            StageCreated(
                organization_id=UUID(s.organization_id),
                stage_id=UUID(s.id),
                pipeline_id=UUID(s.pipeline_id),
                name=s.name,
            ),
            db=self.db,
        )
        return StageRead.model_validate(s)

    def update_stage(self, stage_id: str, payload: StageUpdate) -> StageRead:
        s = self.stages_repo.get(stage_id)
        self.stages_repo.update(
            s,
            name=payload.name,
            description=payload.description,
            probability=payload.probability,
            maximum_days=payload.maximum_days,
            entry_requirements=payload.entry_requirements,
            exit_requirements=payload.exit_requirements,
            is_active=payload.is_active,
        )
        return StageRead.model_validate(s)

    def get_default(self) -> PipelineWithStages | None:
        """Return the default active pipeline for the current tenant, if any."""
        for p in self.repo.list_all():
            if p.is_default:
                return self.get(p.id)
        return None
