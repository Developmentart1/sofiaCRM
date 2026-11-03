"""Reports module tests — KPIs exact values, summary range filter, performance
per user, and the dashboard's recent/upcoming/stuck endpoints."""
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

import pytest
import sqlalchemy as sa

from core.database import SessionLocal
from core.tenant import org_scope
from modules.opportunities.domain import Opportunity
from modules.reports.service import ReportService

import helpers as h


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _insert_opportunity(
    db,
    org_id,
    pipeline_id,
    stage_id,
    *,
    name="Opp",
    status="open",
    estimated=0,
    won=None,
    closed_at=None,
    owner=None,
    entered_at=None,
):
    opp_id = uuid4().hex
    db.execute(
        sa.text(
            "INSERT INTO opportunities (id, organization_id, pipeline_id, stage_id, name, "
            "status, estimated_value, won_value, closed_at, assigned_user_id, entered_stage_at, "
            "created_at, updated_at) "
            "VALUES (:id, :org, :pipe, :stage, :name, :status, :est, :won, :closed, :owner, "
            ":entered, :t, :t)"
        ),
        {
            "id": opp_id,
            "org": org_id,
            "pipe": pipeline_id,
            "stage": stage_id,
            "name": name,
            "status": status,
            "est": estimated,
            "won": won,
            "closed": closed_at,
            "owner": owner,
            "entered": entered_at or _now(),
            "t": _now(),
        },
    )
    return opp_id


def _seed_pipeline(db, org_id):
    return h.insert_pipeline_and_stages(db, org_id)


def test_kpis_exact_values(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    pipe, stages = _seed_pipeline(db, org)
    h.insert_contact(db, org, "A")
    h.insert_contact(db, org, "B")
    # third contact created last month → excluded from contacts_added_this_month
    old = _now() - timedelta(days=40)
    db.execute(
        sa.text(
            "INSERT INTO contacts (id, organization_id, type, first_name, last_name, created_at, updated_at) "
            "VALUES (:id, :org, 'PF', 'Old', 'Contact', :t, :t)"
        ),
        {"id": uuid4().hex, "org": org, "t": old},
    )
    h.insert_company(db, org, "ACME")

    _insert_opportunity(db, org, pipe, stages["open"], name="open1", status="open", estimated=1000)
    _insert_opportunity(
        db, org, pipe, stages["won"], name="won1", status="won", estimated=5000, won=5000, closed_at=_now()
    )
    _insert_opportunity(db, org, pipe, stages["lost"], name="lost1", status="lost", estimated=2000)

    today = _now().date()
    yesterday = today - timedelta(days=1)
    h.insert_task(db, org, user, title="overdue", status="pending", due_date=yesterday)
    h.insert_task(db, org, user, title="today", status="pending", due_date=today)
    h.insert_task(db, org, user, title="done", status="completed", due_date=today)

    db.commit()
    db.close()

    resp = client.get("/api/v1/reports/kpis", headers=_headers(h.make_token(org, user)))
    assert resp.status_code == 200, resp.text
    k = resp.json()

    assert k["total_contacts"] == 3
    assert k["total_companies"] == 1
    assert k["total_opportunities"] == 3
    assert k["open_opportunities_value"] == 1000.0
    assert k["won_opportunities_value"] == 5000.0
    assert k["won_opportunities_count"] == 1
    assert k["lost_opportunities_count"] == 1
    assert k["conversion_rate"] == 0.5
    assert k["average_deal_size"] == 5000.0
    assert k["pipeline_velocity"] == pytest.approx(5000.0 / 30)
    assert k["overdue_tasks"] == 1
    assert k["tasks_due_today"] == 1
    assert k["contacts_added_this_month"] == 2
    assert k["opportunities_won_this_month"] == 1


def test_summary_with_range_filter(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    pipe, stages = _seed_pipeline(db, org)

    jan = datetime(2026, 1, 10, 0, 0, 0)
    feb = datetime(2026, 2, 10, 0, 0, 0)
    _insert_opportunity(db, org, pipe, stages["won"], name="won-jan", status="won", estimated=1000, won=1000, closed_at=jan, owner=user)
    _insert_opportunity(db, org, pipe, stages["won"], name="won-feb", status="won", estimated=2000, won=2000, closed_at=feb, owner=user)
    db.commit()
    db.close()

    headers = _headers(h.make_token(org, user))

    jan_only = client.get("/api/v1/reports/summary", params={"from": "2026-01-01", "to": "2026-01-31"}, headers=headers)
    assert jan_only.status_code == 200, jan_only.text
    j = jan_only.json()
    assert j["total_revenue"] == 1000.0
    assert j["period_start"] == "2026-01-01"
    assert j["period_end"] == "2026-01-31"
    assert j["revenue_by_pipeline"][0]["revenue"] == 1000.0
    assert j["revenue_by_owner"][0]["revenue"] == 1000.0

    both = client.get("/api/v1/reports/summary", params={"from": "2026-01-01", "to": "2026-02-28"}, headers=headers)
    assert both.json()["total_revenue"] == 3000.0


def test_performance_by_user(client):
    db = SessionLocal()
    org = h.insert_org(db)
    u1 = h.insert_user(db, org, role="admin", email="u1@test.mx")
    u2 = h.insert_user(db, org, role="asesor", email="u2@test.mx")
    pipe, stages = _seed_pipeline(db, org)

    now = _now()
    _insert_opportunity(db, org, pipe, stages["won"], name="w", status="won", estimated=100, won=100, closed_at=now, owner=u1)
    _insert_opportunity(db, org, pipe, stages["open"], name="o", status="open", estimated=50, owner=u1)
    h.insert_activity(db, org, u1, type_="note", occurred_at=now)
    h.insert_task(db, org, u1, title="done", status="completed", due_date=_now().date())
    db.execute(
        sa.text(
            "UPDATE tasks SET completed_at = :t WHERE assigned_user_id = :u AND status = 'completed'"
        ),
        {"t": now, "u": u1},
    )
    db.commit()
    db.close()

    headers = _headers(h.make_token(org, u1))
    resp = client.get("/api/v1/reports/performance", params={"from": (now - timedelta(days=1)).date().isoformat(), "to": now.date().isoformat()}, headers=headers)
    assert resp.status_code == 200, resp.text
    perf = {p["user_id"]: p for p in resp.json()}

    assert perf[u1]["opportunities_won"] == 1
    assert perf[u1]["opportunities_won_value"] == 100.0
    assert perf[u1]["opportunities_open"] == 1
    assert perf[u1]["activities_logged"] == 1
    assert perf[u1]["tasks_completed"] == 1
    # u2 has no activity → zeros
    assert perf[u2]["opportunities_won"] == 0
    assert perf[u2]["tasks_completed"] == 0


def test_recent_activities_endpoint(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()

    headers = _headers(h.make_token(org, user))
    # Explicit occurred_at: the Windows clock ticks every ~2ms, so two rapid
    # creates can tie on occurred_at AND created_at and make ORDER BY ambiguous.
    base = _now() - timedelta(hours=2)
    r1 = client.post(
        "/api/v1/activities",
        json={"type": "call", "subject": "older", "occurred_at": base.isoformat()},
        headers=headers,
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        "/api/v1/activities",
        json={
            "type": "note",
            "subject": "latest",
            "occurred_at": (base + timedelta(hours=1)).isoformat(),
        },
        headers=headers,
    )
    assert r2.status_code == 201, r2.text

    resp = client.get("/api/v1/activities/recent", params={"limit": 1}, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["subject"] == "latest"


def test_upcoming_tasks_endpoint(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()

    headers = _headers(h.make_token(org, user))
    tomorrow = (_now().date() + timedelta(days=1)).isoformat()
    yesterday = (_now().date() - timedelta(days=1)).isoformat()
    client.post("/api/v1/tasks", json={"title": "soon", "due_date": tomorrow}, headers=headers)
    client.post("/api/v1/tasks", json={"title": "past", "due_date": yesterday}, headers=headers)
    client.post("/api/v1/tasks", json={"title": "done", "status": "completed"}, headers=headers)

    resp = client.get("/api/v1/tasks/upcoming", params={"limit": 10}, headers=headers)
    assert resp.status_code == 200, resp.text
    titles = [t["title"] for t in resp.json()]
    assert "soon" in titles
    assert "past" not in titles
    assert "done" not in titles


def test_stuck_opportunities_endpoint(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    pipe, stages = _seed_pipeline(db, org)

    old = _now() - timedelta(days=30)
    fresh = _now()
    _insert_opportunity(db, org, pipe, stages["open"], name="stuck", status="open", estimated=100, entered_at=old)
    _insert_opportunity(db, org, pipe, stages["open"], name="fresh", status="open", estimated=200, entered_at=fresh)
    db.commit()
    db.close()

    headers = _headers(h.make_token(org, user))
    resp = client.get("/api/v1/opportunities/stuck", params={"days": 14}, headers=headers)
    assert resp.status_code == 200, resp.text
    names = [o["name"] for o in resp.json()]
    assert "stuck" in names
    assert "fresh" not in names


def test_summary_includes_boundary_dates(client):
    """Una oportunidad cerrada exactamente en los límites del período se incluye."""
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    pipe, stages = _seed_pipeline(db, org)

    fecha_inicio = date(2026, 3, 15)
    lower_bound = datetime.combine(fecha_inicio, time.min)
    upper_bound = datetime.combine(fecha_inicio, time.max)
    db.add_all(
        [
            Opportunity(
                organization_id=org,
                pipeline_id=pipe,
                stage_id=stages["won"],
                name="won-lower",
                status="won",
                estimated_value=1000,
                won_value=1000,
                closed_at=lower_bound,
                assigned_user_id=user,
            ),
            Opportunity(
                organization_id=org,
                pipeline_id=pipe,
                stage_id=stages["won"],
                name="won-upper",
                status="won",
                estimated_value=2000,
                won_value=2000,
                closed_at=upper_bound,
                assigned_user_id=user,
            ),
        ]
    )
    db.commit()

    with org_scope(org):
        result = ReportService(db).summary(from_=fecha_inicio, to=fecha_inicio)

    assert result.total_revenue == 3000.0
    # Also verify pipeline breakdown includes both boundary opps
    assert result.revenue_by_pipeline[0].revenue == 3000.0
    db.close()


def test_kpis_boundary_velocity_window(client):
    """Won opp cerrada EXACTAMENTE en velocity_window_start debe incluirse en pipeline_velocity."""
    from freezegun import freeze_time
    from modules.opportunities.domain import Opportunity as OppModel
    from modules.reports.service import _VELOCITY_WINDOW_DAYS

    frozen = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    with freeze_time(frozen):
        db = SessionLocal()
        org = h.insert_org(db)
        user = h.insert_user(db, org, role="admin")
        pipe, stages = _seed_pipeline(db, org)

        velocity_start = frozen - timedelta(days=_VELOCITY_WINDOW_DAYS)
        db.add(OppModel(
            organization_id=org, pipeline_id=pipe, stage_id=stages["won"],
            name="boundary-velocity", status="won",
            estimated_value=100, won_value=100,
            closed_at=velocity_start, assigned_user_id=user,
        ))
        db.commit()

        with org_scope(org):
            k = ReportService(db).kpis()

        assert k.pipeline_velocity > 0, (
            f"velocity={k.pipeline_velocity}, boundary opp at {velocity_start} excluded"
        )
        db.close()


def test_kpis_boundary_month_start(client):
    """Contact creado EXACTAMENTE en month_start debe incluirse en contacts_added_this_month."""
    from freezegun import freeze_time
    from modules.contacts.domain import Contact as ContactModel

    frozen = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    with freeze_time(frozen):
        db = SessionLocal()
        org = h.insert_org(db)
        user = h.insert_user(db, org, role="admin")

        month_start = frozen.date().replace(day=1)
        month_start_dt = datetime.combine(month_start, time.min)
        db.add(ContactModel(
            organization_id=org, type="PF",
            first_name="Boundary", last_name="Contact",
            created_at=month_start_dt, updated_at=month_start_dt,
        ))
        db.commit()

        with org_scope(org):
            k = ReportService(db).kpis()

        assert k.contacts_added_this_month >= 1, (
            f"contacts={k.contacts_added_this_month}, boundary contact at {month_start_dt} excluded"
        )
        db.close()


def test_pipeline_distribution_excludes_inactive_stages(client):
    """Una etapa con is_active=False no debe aparecer en la distribución."""
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    pipe, stages = _seed_pipeline(db, org)

    inactive_stage_id = uuid4().hex
    db.execute(
        sa.text(
            "INSERT INTO pipeline_stages (id, organization_id, pipeline_id, name, position, "
            "probability, stage_type, is_active, created_at, updated_at) "
            "VALUES (:id, :org, :pipe, :name, :pos, :prob, :stype, 0, :t, :t)"
        ),
        {
            "id": inactive_stage_id,
            "org": org,
            "pipe": pipe,
            "name": "Archived Stage",
            "pos": 99,
            "prob": 0,
            "stype": "open",
            "t": _now(),
        },
    )
    _insert_opportunity(db, org, pipe, inactive_stage_id, name="opp-archived", status="open", estimated=500)
    db.commit()

    with org_scope(org):
        result = ReportService(db).pipeline_distribution()

    stage_names = [s["stage_name"] for s in result]
    assert "Archived Stage" not in stage_names
    db.close()


def test_kpis_boundary_won_this_month(client):
    """Won opp cerrada EXACTAMENTE en month_start debe contar en opportunities_won_this_month."""
    from freezegun import freeze_time
    from modules.opportunities.domain import Opportunity as OppModel

    frozen = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    with freeze_time(frozen):
        db = SessionLocal()
        org = h.insert_org(db)
        user = h.insert_user(db, org, role="admin")
        pipe, stages = _seed_pipeline(db, org)

        month_start_dt = datetime.combine(frozen.date().replace(day=1), time.min)
        db.add(OppModel(
            organization_id=org, pipeline_id=pipe, stage_id=stages["won"],
            name="boundary-won-month", status="won",
            estimated_value=100, won_value=100,
            closed_at=month_start_dt, assigned_user_id=user,
        ))
        db.commit()

        with org_scope(org):
            k = ReportService(db).kpis()

        assert k.opportunities_won_this_month >= 1, (
            f"won_this_month={k.opportunities_won_this_month}, boundary opp "
            f"closed exactly at {month_start_dt} excluded"
        )
        db.close()


def test_summary_boundary_revenue_by_owner(client):
    """Won opps cerradas EXACTAMENTE en from_dt y to_dt deben sumar en revenue_by_owner."""
    from modules.opportunities.domain import Opportunity as OppModel

    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    pipe, stages = _seed_pipeline(db, org)

    from_date = date(2026, 6, 1)
    to_date = date(2026, 6, 30)
    db.add(OppModel(
        organization_id=org, pipeline_id=pipe, stage_id=stages["won"],
        name="at-from", status="won", estimated_value=100, won_value=100,
        closed_at=datetime.combine(from_date, time.min), assigned_user_id=user,
    ))
    db.add(OppModel(
        organization_id=org, pipeline_id=pipe, stage_id=stages["won"],
        name="at-to", status="won", estimated_value=200, won_value=200,
        closed_at=datetime.combine(to_date, time.max), assigned_user_id=user,
    ))
    db.commit()

    with org_scope(org):
        s = ReportService(db).summary(from_=from_date, to=to_date)

    by_owner = {r.user_id: r for r in s.revenue_by_owner}
    assert user in by_owner, "boundary opps excluded from revenue_by_owner"
    assert by_owner[user].revenue == 300.0, (
        f"revenue={by_owner[user].revenue}, expected 300.0 "
        f"(opps closed exactly on from/to boundary)"
    )
    db.close()


def test_performance_boundary_window(client):
    """Won/activity/task EXACTAMENTE en los límites del rango deben contarse en performance."""
    from modules.activities.domain import Activity as ActivityModel
    from modules.opportunities.domain import Opportunity as OppModel
    from modules.tasks.domain import Task as TaskModel

    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    pipe, stages = _seed_pipeline(db, org)

    from_date = date(2026, 6, 1)
    to_date = date(2026, 6, 30)
    from_dt = datetime.combine(from_date, time.min)
    to_dt = datetime.combine(to_date, time.max)

    db.add(OppModel(
        organization_id=org, pipeline_id=pipe, stage_id=stages["won"],
        name="w-from", status="won", estimated_value=100, won_value=100,
        closed_at=from_dt, assigned_user_id=user,
    ))
    db.add(OppModel(
        organization_id=org, pipeline_id=pipe, stage_id=stages["won"],
        name="w-to", status="won", estimated_value=200, won_value=200,
        closed_at=to_dt, assigned_user_id=user,
    ))
    db.add(ActivityModel(
        organization_id=org, user_id=user, type="note",
        subject="at-from", occurred_at=from_dt,
    ))
    db.add(ActivityModel(
        organization_id=org, user_id=user, type="note",
        subject="at-to", occurred_at=to_dt,
    ))
    db.add(TaskModel(
        organization_id=org, assigned_user_id=user, title="t-from",
        status="completed", completed_at=from_dt,
    ))
    db.add(TaskModel(
        organization_id=org, assigned_user_id=user, title="t-to",
        status="completed", completed_at=to_dt,
    ))
    db.commit()

    with org_scope(org):
        perf = ReportService(db).performance(from_=from_date, to=to_date)

    row = next((r for r in perf if r.user_id == user), None)
    assert row is not None, "user missing from performance"
    assert row.opportunities_won == 2, (
        f"won={row.opportunities_won}, expected 2 (boundary closed_at excluded)"
    )
    assert row.activities_logged == 2, (
        f"activities={row.activities_logged}, expected 2 (boundary occurred_at excluded)"
    )
    assert row.tasks_completed == 2, (
        f"tasks={row.tasks_completed}, expected 2 (boundary completed_at excluded)"
    )
    db.close()


def test_pipeline_trend_boundary_last_day(client):
    """Opp abierta creada EXACTAMENTE en el cierre del último día debe contar en el trend."""
    from freezegun import freeze_time
    from modules.opportunities.domain import Opportunity as OppModel

    frozen = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    with freeze_time(frozen):
        db = SessionLocal()
        org = h.insert_org(db)
        user = h.insert_user(db, org, role="admin")
        pipe, stages = _seed_pipeline(db, org)

        created_at = datetime.combine(frozen.date(), time.max)
        db.add(OppModel(
            organization_id=org, pipeline_id=pipe, stage_id=stages["open"],
            name="trend-boundary", status="open", estimated_value=5000,
            created_at=created_at, assigned_user_id=user,
        ))
        db.commit()

        with org_scope(org):
            trend = ReportService(db).pipeline_trend(days=3)

        assert float(trend[-1]["value"]) == 5000.0, (
            f"last day value={trend[-1]['value']}, opp created exactly at "
            f"{created_at} excluded"
        )
        assert float(trend[0]["value"]) == 0.0, "value leaks into days before creation"
        db.close()
