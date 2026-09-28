"""Reports routes — read-only aggregations, tenant-scoped, RBAC-protected."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from .schemas import DashboardKPIs, ReportSummary, UserPerformance
from .service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/kpis", response_model=DashboardKPIs)
def kpis(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.REPORT_READ)
    return ReportService(db).kpis()


@router.get("/summary", response_model=ReportSummary)
def summary(
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None, alias="to"),
    pipeline_id: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.REPORT_READ)
    return ReportService(db).summary(from_=from_, to=to, pipeline_id=pipeline_id)


@router.get("/performance", response_model=list[UserPerformance])
def performance(
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None, alias="to"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.REPORT_READ)
    return ReportService(db).performance(from_=from_, to=to)


@router.get("/pipeline/trend")
def pipeline_trend(
    days: int = Query(7, ge=1, le=90),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Pipeline value trend over the last N days."""
    require_permission(current.role, Permission.REPORT_READ)
    return ReportService(db).pipeline_trend(days=days)


@router.get("/pipeline/distribution")
def pipeline_distribution(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Opportunity count distribution by pipeline stage."""
    require_permission(current.role, Permission.REPORT_READ)
    return ReportService(db).pipeline_distribution()
