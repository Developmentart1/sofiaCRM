"""Activities routes — timeline listing, manual creation and deletion."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.pagination import PaginatedResponse
from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from .schemas import ActivityCreate, ActivityRead
from .service import ActivityService

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=PaginatedResponse[ActivityRead])
def list_activities(
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=200),
    type: str | None = None,
    contact_id: str | None = None,
    opportunity_id: str | None = None,
    company_id: str | None = None,
    user_id: str | None = None,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None, alias="to"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.ACTIVITY_READ)
    return ActivityService(db).list_activities(
        type=type,
        contact_id=contact_id,
        opportunity_id=opportunity_id,
        company_id=company_id,
        user_id=user_id,
        from_=from_,
        to=to,
        page=page,
        page_size=page_size,
    )


@router.get("/recent", response_model=list[ActivityRead])
def recent_activities(
    limit: int = Query(10, ge=1, le=100),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.ACTIVITY_READ)
    return ActivityService(db).list_recent(limit=limit)


@router.post("", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
def create_activity(
    data: ActivityCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.ACTIVITY_CREATE)
    return ActivityService(db).create_activity(data, current.id)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.ACTIVITY_DELETE)
    ActivityService(db).delete_activity(activity_id)
