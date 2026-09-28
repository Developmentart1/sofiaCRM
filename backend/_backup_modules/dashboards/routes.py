"""Dashboard read-only routes. All aggregations are SQL-side."""
from __future__ import annotations

from fastapi import APIRouter, Query

from core.errors import ForbiddenError
from core.rbac import Permission, role_has
from modules.users.auth_deps import CurrentUserDep, DbSessionDep
from .schemas import (
    FunnelRead,
    KpiRead,
    PerformanceRead,
    SourcesRead,
)
from .service import DashboardService

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _require(role: str) -> None:
    if not role_has(role, Permission.DASHBOARD_READ):
        raise ForbiddenError("role lacks dashboard:read")


@router.get("/kpis", response_model=KpiRead)
def kpis(current: CurrentUserDep, db: DbSessionDep) -> KpiRead:
    _require(current.role)
    return DashboardService(db).kpis()


@router.get("/funnel", response_model=FunnelRead)
def funnel(
    pipeline_id: str | None = Query(default=None),
    current: CurrentUserDep = None,
    db: DbSessionDep = None,
) -> FunnelRead:
    _require(current.role)
    return DashboardService(db).funnel(pipeline_id=pipeline_id)


@router.get("/performance", response_model=PerformanceRead)
def performance(current: CurrentUserDep, db: DbSessionDep) -> PerformanceRead:
    _require(current.role)
    return DashboardService(db).performance()


@router.get("/sources", response_model=SourcesRead)
def sources(current: CurrentUserDep, db: DbSessionDep) -> SourcesRead:
    _require(current.role)
    return DashboardService(db).sources()
