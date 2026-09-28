"""Reports module tests — KPIs exact values, summary range filter, performance
per user, and the dashboard's recent/upcoming/stuck endpoints."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import sqlalchemy as sa

from core.database import SessionLocal

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
    client.post("/api/v1/activities", json={"type": "call", "subject": "older"}, headers=headers)
    client.post("/api/v1/activities", json={"type": "note", "subject": "latest"}, headers=headers)

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
