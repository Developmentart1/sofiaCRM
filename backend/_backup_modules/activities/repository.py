"""Activities + Tasks repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.tenant import current_org_id
from .domain import Activity, Task


class ActivityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, act_id: str) -> Activity:
        org = current_org_id()
        stmt = select(Activity).where(Activity.id == act_id, Activity.organization_id == org)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"activity {act_id} not found")
        return row

    def list_filtered(
        self,
        *,
        opportunity_id: str | None = None,
        contact_id: str | None = None,
        assigned_user_id: str | None = None,
        limit: int = 100,
    ) -> list[Activity]:
        org = current_org_id()
        stmt = select(Activity).where(Activity.organization_id == org)
        if opportunity_id is not None:
            stmt = stmt.where(Activity.opportunity_id == opportunity_id)
        if contact_id is not None:
            stmt = stmt.where(Activity.contact_id == contact_id)
        if assigned_user_id is not None:
            stmt = stmt.where(Activity.assigned_user_id == assigned_user_id)
        stmt = stmt.order_by(Activity.occurred_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **kwargs) -> Activity:
        org = current_org_id()
        a = Activity(organization_id=org, **kwargs)
        self.db.add(a)
        self.db.flush()
        return a


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, task_id: str) -> Task:
        org = current_org_id()
        stmt = select(Task).where(Task.id == task_id, Task.organization_id == org)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"task {task_id} not found")
        return row

    def list_filtered(
        self,
        *,
        opportunity_id: str | None = None,
        assigned_user_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[Task]:
        org = current_org_id()
        stmt = select(Task).where(Task.organization_id == org)
        if opportunity_id is not None:
            stmt = stmt.where(Task.opportunity_id == opportunity_id)
        if assigned_user_id is not None:
            stmt = stmt.where(Task.assigned_user_id == assigned_user_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.due_at.asc().nullslast(), Task.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def next_pending_for_opportunity(self, opportunity_id: str) -> Task | None:
        org = current_org_id()
        from datetime import UTC, datetime

        stmt = (
            select(Task)
            .where(
                Task.organization_id == org,
                Task.opportunity_id == opportunity_id,
                Task.status == "pending",
            )
            .order_by(Task.due_at.asc().nullslast())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def overdue_count(self) -> int:
        from datetime import UTC, datetime

        from sqlalchemy import func

        org = current_org_id()
        stmt = select(func.count(Task.id)).where(
            Task.organization_id == org,
            Task.status == "pending",
            Task.due_at.isnot(None),
            Task.due_at < datetime.now(UTC),
        )
        return int(self.db.execute(stmt).scalar_one() or 0)

    def create(self, **kwargs) -> Task:
        org = current_org_id()
        t = Task(organization_id=org, **kwargs)
        self.db.add(t)
        self.db.flush()
        return t

    def update(self, t: Task, **kwargs) -> Task:
        for k, v in kwargs.items():
            if v is not None:
                setattr(t, k, v)
        self.db.flush()
        return t
