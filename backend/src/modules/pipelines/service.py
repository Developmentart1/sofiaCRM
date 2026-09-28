"""Pipeline service."""
from uuid import UUID

from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.event_bus import PipelineCreated, StageCreated, get_bus
from core.tenant import current_org_id
from .domain import Pipeline, Stage
from .schemas import PipelineCreate, StageCreate


class PipelineService:
    def __init__(self, db: Session):
        self.db = db

    def list_pipelines(self) -> list[Pipeline]:
        org = current_org_id()
        return self.db.query(Pipeline).filter(
            Pipeline.organization_id == org
        ).order_by(Pipeline.name).all()

    def get_pipeline(self, pid: str) -> Pipeline:
        org = current_org_id()
        p = self.db.query(Pipeline).filter(
            Pipeline.id == pid, Pipeline.organization_id == org
        ).first()
        if not p:
            raise NotFoundError(f"pipeline {pid} not found")
        return p

    def create_pipeline(self, data: PipelineCreate) -> Pipeline:
        org = current_org_id()
        p = Pipeline(organization_id=org, **data.model_dump())
        self.db.add(p)
        self.db.flush()
        get_bus().publish(
            PipelineCreated(organization_id=UUID(org), pipeline_id=UUID(p.id), name=p.name),
            db=self.db,
        )
        self.db.commit()
        return p

    def list_stages(self, pipeline_id: str) -> list[Stage]:
        org = current_org_id()
        self.get_pipeline(pipeline_id)  # validates ownership
        return self.db.query(Stage).filter(
            Stage.pipeline_id == pipeline_id, Stage.organization_id == org
        ).order_by(Stage.position).all()

    def create_stage(self, pipeline_id: str, data: StageCreate) -> Stage:
        org = current_org_id()
        self.get_pipeline(pipeline_id)
        s = Stage(organization_id=org, pipeline_id=pipeline_id, **data.model_dump())
        self.db.add(s)
        self.db.flush()
        get_bus().publish(
            StageCreated(
                organization_id=UUID(org),
                stage_id=UUID(s.id),
                pipeline_id=UUID(pipeline_id),
                name=s.name,
            ),
            db=self.db,
        )
        self.db.commit()
        return s
