"""Pipelines + Stages repository. Every read scoped by organization_id."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import Pipeline, Stage


class PipelineRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, pipeline_id: str) -> Pipeline:
        org = current_org_id()
        stmt = select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.organization_id == org)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"pipeline {pipeline_id} not found")
        return row

    def list_all(self) -> list[Pipeline]:
        org = current_org_id()
        stmt = (
            select(Pipeline)
            .where(Pipeline.organization_id == org, Pipeline.is_active.is_(True))
            .order_by(Pipeline.is_default.desc(), Pipeline.name.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        *,
        name: str,
        description: str | None,
        entity_type: str,
        is_default: bool,
        is_active: bool,
    ) -> Pipeline:
        org = current_org_id()
        p = Pipeline(
            organization_id=org,
            name=name,
            description=description,
            entity_type=entity_type,
            is_default=is_default,
            is_active=is_active,
        )
        self.db.add(p)
        self.db.flush()
        return p

    def update(
        self,
        p: Pipeline,
        *,
        name: str | None = None,
        description: str | None = None,
        is_default: bool | None = None,
        is_active: bool | None = None,
    ) -> Pipeline:
        if name is not None:
            p.name = name
        if description is not None:
            p.description = description
        if is_default is not None:
            p.is_default = is_default
        if is_active is not None:
            p.is_active = is_active
        self.db.flush()
        return p


class StageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, stage_id: str) -> Stage:
        org = current_org_id()
        stmt = select(Stage).where(Stage.id == stage_id, Stage.organization_id == org)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"stage {stage_id} not found")
        return row

    def list_by_pipeline(self, pipeline_id: str) -> list[Stage]:
        org = current_org_id()
        stmt = (
            select(Stage)
            .where(Stage.pipeline_id == pipeline_id, Stage.organization_id == org)
            .order_by(Stage.position.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        *,
        pipeline_id: str,
        name: str,
        description: str | None,
        position: int,
        stage_type: str,
        probability: int,
        maximum_days: int | None,
        entry_requirements: str | None,
        exit_requirements: str | None,
        is_active: bool,
    ) -> Stage:
        org = current_org_id()
        s = Stage(
            organization_id=org,
            pipeline_id=pipeline_id,
            name=name,
            description=description,
            position=position,
            stage_type=stage_type,
            probability=probability,
            maximum_days=maximum_days,
            entry_requirements=entry_requirements,
            exit_requirements=exit_requirements,
            is_active=is_active,
        )
        self.db.add(s)
        self.db.flush()
        return s

    def update(
        self,
        s: Stage,
        *,
        name: str | None = None,
        description: str | None = None,
        probability: int | None = None,
        maximum_days: int | None = None,
        entry_requirements: str | None = None,
        exit_requirements: str | None = None,
        is_active: bool | None = None,
    ) -> Stage:
        if name is not None:
            s.name = name
        if description is not None:
            s.description = description
        if probability is not None:
            s.probability = probability
        if maximum_days is not None:
            s.maximum_days = maximum_days
        if entry_requirements is not None:
            s.entry_requirements = entry_requirements
        if exit_requirements is not None:
            s.exit_requirements = exit_requirements
        if is_active is not None:
            s.is_active = is_active
        self.db.flush()
        return s
