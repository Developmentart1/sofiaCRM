"""Activities + Tasks routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from core.audit import audit_log
from core.errors import ForbiddenError
from core.event_bus import get_bus
from core.rbac import Permission, role_has
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
from .schemas import (
    ActivityCreate,
    ActivityRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)
from .service import ActivityService, TaskService

router = APIRouter(tags=["activities"])


def _service(db):
    return ActivityService(db, get_bus())


def _tasks(db):
    return TaskService(db, get_bus())


@router.get("/activities", response_model=list[ActivityRead])
def list_activities(
    opportunity_id: UUID | None = None,
    contact_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> list[ActivityRead]:
    if not role_has(current.role, Permission.ACTIVITY_READ):
        raise ForbiddenError("role lacks activity:read")
    return _service(db).list(
        opportunity_id=str(opportunity_id) if opportunity_id else None,
        contact_id=str(contact_id) if contact_id else None,
        assigned_user_id=str(assigned_user_id) if assigned_user_id else None,
    )


@router.post("/activities", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
@audit_log("activity.create", entity_type="activity")
def create_activity(
    payload: ActivityCreate, current: CurrentUserDep, db: DbSessionDep
) -> ActivityRead:
    if not role_has(current.role, Permission.ACTIVITY_CREATE):
        raise ForbiddenError("role lacks activity:create")
    return _service(db).create(payload, performed_by=current.id)


@router.get("/activities/{act_id}", response_model=ActivityRead)
def get_activity(act_id: str, current: CurrentUserDep, db: DbSessionDep) -> ActivityRead:
    if not role_has(current.role, Permission.ACTIVITY_READ):
        raise ForbiddenError("role lacks activity:read")
    return _service(db).get(act_id)


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(
    opportunity_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> list[TaskRead]:
    if not role_has(current.role, Permission.ACTIVITY_READ):
        raise ForbiddenError("role lacks activity:read")
    return _tasks(db).list(
        opportunity_id=str(opportunity_id) if opportunity_id else None,
        assigned_user_id=str(assigned_user_id) if assigned_user_id else None,
        status=status_filter,
    )


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
@audit_log("task.create", entity_type="task")
def create_task(
    payload: TaskCreate, current: CurrentUserDep, db: DbSessionDep
) -> TaskRead:
    if not role_has(current.role, Permission.ACTIVITY_CREATE):
        raise ForbiddenError("role lacks activity:create")
    return _tasks(db).create(payload, created_by=current.id)


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: str, current: CurrentUserDep, db: DbSessionDep) -> TaskRead:
    if not role_has(current.role, Permission.ACTIVITY_READ):
        raise ForbiddenError("role lacks activity:read")
    return _tasks(db).get(task_id)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
@audit_log("task.update", entity_type="task")
def update_task(
    task_id: str, payload: TaskUpdate, current: CurrentUserDep, db: DbSessionDep
) -> TaskRead:
    if not role_has(current.role, Permission.ACTIVITY_UPDATE):
        raise ForbiddenError("role lacks activity:update")
    return _tasks(db).update(task_id, payload)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log("task.delete", entity_type="task")
def delete_task(task_id: str, current: CurrentUserDep, db: DbSessionDep) -> None:
    if not role_has(current.role, Permission.ACTIVITY_UPDATE):
        raise ForbiddenError("role lacks activity:update")
    _tasks(db).delete(task_id)
