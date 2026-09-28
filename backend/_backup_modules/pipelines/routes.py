"""Pipelines module routes."""
from __future__ import annotations

from fastapi import APIRouter, status

from core.audit import audit_log
from core.event_bus import get_bus
from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
from .schemas import (
    PipelineCreate,
    PipelineRead,
    PipelineUpdate,
    PipelineWithStages,
    StageCreate,
    StageRead,
    StageUpdate,
)
from .service import PipelineService

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _service(db):
    return PipelineService(db, get_bus())


@router.get("", response_model=list[PipelineRead])
def list_pipelines(current: CurrentUserDep, db: DbSessionDep) -> list[PipelineRead]:
    require_permission(current.role, Permission.PIPELINE_READ)
    return _service(db).list()


@router.post("", response_model=PipelineWithStages, status_code=status.HTTP_201_CREATED)
@audit_log("pipeline.create", entity_type="pipeline")
def create_pipeline(
    payload: PipelineCreate, current: CurrentUserDep, db: DbSessionDep
) -> PipelineWithStages:
    require_permission(current.role, Permission.PIPELINE_MANAGE)
    return _service(db).create(payload)


@router.get("/{pipeline_id}", response_model=PipelineWithStages)
def get_pipeline(pipeline_id: str, current: CurrentUserDep, db: DbSessionDep) -> PipelineWithStages:
    require_permission(current.role, Permission.PIPELINE_READ)
    return _service(db).get(pipeline_id)


@router.patch("/{pipeline_id}", response_model=PipelineRead)
@audit_log("pipeline.update", entity_type="pipeline")
def update_pipeline(
    pipeline_id: str, payload: PipelineUpdate, current: CurrentUserDep, db: DbSessionDep
) -> PipelineRead:
    require_permission(current.role, Permission.PIPELINE_MANAGE)
    return _service(db).update(pipeline_id, payload)


@router.post(
    "/{pipeline_id}/stages", response_model=StageRead, status_code=status.HTTP_201_CREATED
)
@audit_log("stage.create", entity_type="stage")
def add_stage(
    pipeline_id: str, payload: StageCreate, current: CurrentUserDep, db: DbSessionDep
) -> StageRead:
    require_permission(current.role, Permission.PIPELINE_MANAGE)
    return _service(db).add_stage(pipeline_id, payload)


@router.patch("/stages/{stage_id}", response_model=StageRead)
@audit_log("stage.update", entity_type="stage")
def update_stage(
    stage_id: str, payload: StageUpdate, current: CurrentUserDep, db: DbSessionDep
) -> StageRead:
    require_permission(current.role, Permission.PIPELINE_MANAGE)
    return _service(db).update_stage(stage_id, payload)
