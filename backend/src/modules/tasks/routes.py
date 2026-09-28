"""Tasks routes — CRUD + filters, tenant-scoped, RBAC-protected."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.pagination import PaginatedResponse
from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from .schemas import TaskCreate, TaskRead, TaskUpdate
from .service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=PaginatedResponse[TaskRead])
def list_tasks(
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=200),
    search: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    owner_id: str | None = None,
    contact_id: str | None = None,
    opportunity_id: str | None = None,
    company_id: str | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    view: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.TASK_READ)
    return TaskService(db).list_tasks(
        current_user_id=current.id,
        search=search,
        status=status,
        priority=priority,
        owner_id=owner_id,
        contact_id=contact_id,
        opportunity_id=opportunity_id,
        company_id=company_id,
        due_before=due_before,
        due_after=due_after,
        view=view,
        page=page,
        page_size=page_size,
    )


@router.get("/upcoming", response_model=list[TaskRead])
def upcoming_tasks(
    limit: int = Query(10, ge=1, le=100),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.TASK_READ)
    return TaskService(db).list_upcoming(limit=limit)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.TASK_READ)
    return TaskService(db).get_task(task_id)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.TASK_CREATE)
    return TaskService(db).create_task(data, current.id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str,
    data: TaskUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.TASK_UPDATE)
    return TaskService(db).update_task(task_id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.TASK_DELETE)
    TaskService(db).delete_task(task_id)
