"""Pipeline routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from .schemas import PipelineCreate, PipelineDetail, PipelineRead, StageCreate, StageRead
from .service import PipelineService

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("", response_model=list[PipelineRead])
def list_pipelines(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.PIPELINE_READ)
    return PipelineService(db).list_pipelines()


@router.post("", response_model=PipelineRead, status_code=201)
def create_pipeline(
    data: PipelineCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.PIPELINE_CREATE)
    return PipelineService(db).create_pipeline(data)


@router.get("/{pipeline_id}", response_model=PipelineDetail)
def get_pipeline(
    pipeline_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.PIPELINE_READ)
    svc = PipelineService(db)
    pipe = svc.get_pipeline(pipeline_id)
    stages = svc.list_stages(pipeline_id)
    result = PipelineDetail.model_validate(pipe)
    result.stages = [StageRead.model_validate(s) for s in stages]
    return result


@router.get("/{pipeline_id}/stages", response_model=list[StageRead])
def list_stages(
    pipeline_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.PIPELINE_READ)
    return PipelineService(db).list_stages(pipeline_id)


@router.post("/{pipeline_id}/stages", response_model=StageRead, status_code=201)
def create_stage(
    pipeline_id: str,
    data: StageCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.PIPELINE_UPDATE)
    return PipelineService(db).create_stage(pipeline_id, data)
