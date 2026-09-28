"""Activities + Tasks service. RB-013 and RB-014 reconciliation."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from core.errors import ValidationError
from core.event_bus import ActivityCreated, SyncEventBus, TaskCompleted, TaskCreated
from .domain import Activity, Task, TaskStatus
from .repository import ActivityRepository, TaskRepository
from .schemas import (
    ActivityCreate,
    ActivityRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)
from modules.opportunities.domain import Opportunity


class ActivityService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = ActivityRepository(db)

    def list(
        self,
        *,
        opportunity_id: str | None = None,
        contact_id: str | None = None,
        assigned_user_id: str | None = None,
    ) -> list[ActivityRead]:
        rows = self.repo.list_filtered(
            opportunity_id=opportunity_id,
            contact_id=contact_id,
            assigned_user_id=assigned_user_id,
        )
        return [ActivityRead.model_validate(a) for a in rows]

    def get(self, act_id: str) -> ActivityRead:
        return ActivityRead.model_validate(self.repo.get(act_id))

    def create(self, payload: ActivityCreate, *, performed_by: str) -> ActivityRead:
        a = self.repo.create(
            activity_type=payload.activity_type,
            subject=payload.subject,
            description=payload.description,
            opportunity_id=str(payload.opportunity_id) if payload.opportunity_id else None,
            contact_id=str(payload.contact_id) if payload.contact_id else None,
            assigned_user_id=str(payload.assigned_user_id) if payload.assigned_user_id else None,
            performed_by=performed_by,
            occurred_at=payload.occurred_at or datetime.now(UTC),
        )
        self.bus.publish(
            ActivityCreated(
                organization_id=UUID(a.organization_id),
                activity_id=a.uuid,
                activity_type=a.activity_type,
                subject=a.subject,
                opportunity_id=UUID(a.opportunity_id) if a.opportunity_id else None,
                contact_id=UUID(a.contact_id) if a.contact_id else None,
                assigned_user_id=UUID(a.assigned_user_id) if a.assigned_user_id else None,
            ),
            db=self.db,
        )
        return ActivityRead.model_validate(a)


class TaskService:
    def __init__(self, db: Session, bus: SyncEventBus) -> None:
        self.db = db
        self.bus = bus
        self.repo = TaskRepository(db)

    def list(
        self,
        *,
        opportunity_id: str | None = None,
        assigned_user_id: str | None = None,
        status: str | None = None,
    ) -> list[TaskRead]:
        rows = self.repo.list_filtered(
            opportunity_id=opportunity_id,
            assigned_user_id=assigned_user_id,
            status=status,
        )
        return [TaskRead.model_validate(t) for t in rows]

    def get(self, task_id: str) -> TaskRead:
        return TaskRead.model_validate(self.repo.get(task_id))

    def create(self, payload: TaskCreate, *, created_by: str) -> TaskRead:
        t = self.repo.create(
            title=payload.title,
            description=payload.description,
            opportunity_id=str(payload.opportunity_id) if payload.opportunity_id else None,
            assigned_user_id=str(payload.assigned_user_id) if payload.assigned_user_id else None,
            created_by=created_by,
            priority=payload.priority,
            due_at=payload.due_at,
            reminder_at=payload.reminder_at,
            is_overdue=self._is_overdue(payload.due_at),
        )
        self.bus.publish(
            TaskCreated(
                organization_id=UUID(t.organization_id),
                task_id=t.uuid,
                title=t.title,
                due_at=t.due_at,
                assigned_user_id=UUID(t.assigned_user_id) if t.assigned_user_id else None,
                opportunity_id=UUID(t.opportunity_id) if t.opportunity_id else None,
            ),
            db=self.db,
        )
        # RB-014: ensure next_activity_at is correct after creating a task.
        if t.opportunity_id:
            self._recompute_next_activity(t.opportunity_id)
        return TaskRead.model_validate(t)

    def update(self, task_id: str, payload: TaskUpdate) -> TaskRead:
        t = self.repo.get(task_id)
        completing = False
        if payload.title is not None:
            t.title = payload.title
        if payload.description is not None:
            t.description = payload.description
        if payload.priority is not None:
            t.priority = payload.priority
        if payload.due_at is not None:
            t.due_at = payload.due_at
            t.is_overdue = self._is_overdue(t.due_at)
        if payload.reminder_at is not None:
            t.reminder_at = payload.reminder_at
        if payload.status is not None:
            if payload.status == TaskStatus.COMPLETED.value and t.status != TaskStatus.COMPLETED.value:
                completing = True
                t.completed_at = datetime.now(UTC)
                t.is_overdue = False
            t.status = payload.status
        self.db.flush()
        if completing:
            # RB-013: opportunity.last_activity_at updated.
            if t.opportunity_id:
                self._touch_last_activity(t.opportunity_id)
            self.bus.publish(
                TaskCompleted(
                    organization_id=UUID(t.organization_id),
                    task_id=t.uuid,
                ),
                db=self.db,
            )
        # RB-014: keep next_activity_at fresh.
        if t.opportunity_id:
            self._recompute_next_activity(t.opportunity_id)
        return TaskRead.model_validate(t)

    def delete(self, task_id: str) -> None:
        t = self.repo.get(task_id)
        opp_id = t.opportunity_id
        self.db.delete(t)
        self.db.flush()
        if opp_id:
            self._recompute_next_activity(opp_id)

    # ---- RB-013 / RB-014 helpers ----

    def _touch_last_activity(self, opportunity_id: str) -> None:
        opp = self.db.get(Opportunity, opportunity_id)
        if opp is not None:
            opp.last_activity_at = datetime.now(UTC)
            self.db.flush()

    def _recompute_next_activity(self, opportunity_id: str) -> None:
        """RB-014: set opportunity.next_activity_at = earliest pending task.due_at."""
        opp = self.db.get(Opportunity, opportunity_id)
        if opp is None:
            return
        next_task = self.repo.next_pending_for_opportunity(opportunity_id)
        opp.next_activity_at = next_task.due_at if next_task and next_task.due_at else None
        self.db.flush()

    @staticmethod
    def _is_overdue(due_at: datetime | None) -> bool:
        if due_at is None:
            return False
        return due_at < datetime.now(UTC)
