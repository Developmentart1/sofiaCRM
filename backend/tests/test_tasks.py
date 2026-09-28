"""Task module tests — CRUD, filters, derived overdue, tenant isolation, RBAC."""
from datetime import datetime, timedelta, timezone

from core.database import SessionLocal

import helpers as h


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_task_succeeds(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/tasks",
        json={"title": "Call client", "priority": "high"},
        headers=_headers(h.make_token(org, user)),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "Call client"
    assert data["priority"] == "high"
    assert data["status"] == "pending"
    # owner defaults to the current user
    assert data["owner_id"] == user


def test_complete_task_is_idempotent(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()
    token = h.make_token(org, user)
    headers = _headers(token)

    task_id = client.post("/api/v1/tasks", json={"title": "T"}, headers=headers).json()["id"]

    first = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "completed"}, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "completed"
    assert first.json()["completed_at"] is not None

    second = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "completed"}, headers=headers)
    assert second.status_code == 200, second.text
    # idempotent: completed_at is not reset on a second complete
    assert second.json()["completed_at"] == first.json()["completed_at"]


def test_list_view_overdue(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()
    token = h.make_token(org, user)
    headers = _headers(token)

    past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    client.post("/api/v1/tasks", json={"title": "Overdue task", "due_date": past}, headers=headers)

    resp = client.get("/api/v1/tasks", params={"view": "overdue"}, headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert any(t["title"] == "Overdue task" and t["status"] == "overdue" for t in items)


def test_task_tenant_isolation(client):
    db = SessionLocal()
    org_a = h.insert_org(db, "Org A")
    org_b = h.insert_org(db, "Org B")
    user_a = h.insert_user(db, org_a, role="admin")
    user_b = h.insert_user(db, org_b, role="admin")
    db.commit()
    db.close()

    created = client.post(
        "/api/v1/tasks",
        json={"title": "Org A secret task"},
        headers=_headers(h.make_token(org_a, user_a)),
    )
    assert created.status_code == 201, created.text

    resp = client.get("/api/v1/tasks", headers=_headers(h.make_token(org_b, user_b)))
    assert resp.status_code == 200, resp.text
    titles = [t["title"] for t in resp.json()["items"]]
    assert "Org A secret task" not in titles


def test_task_create_denied_for_role_without_permission(client):
    db = SessionLocal()
    org = h.insert_org(db)
    ops = h.insert_user(db, org, role="operaciones")
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/tasks",
        json={"title": "Should fail"},
        headers=_headers(h.make_token(org, ops, role="operaciones")),
    )
    assert resp.status_code == 403, resp.text


def test_task_create_rejects_cross_tenant_opportunity(client):
    db = SessionLocal()
    org_a = h.insert_org(db, "Org A")
    org_b = h.insert_org(db, "Org B")
    user_a = h.insert_user(db, org_a, role="admin")
    user_b = h.insert_user(db, org_b, role="admin")
    pipe_b, stages_b = h.insert_pipeline_and_stages(db, org_b)
    opp_b = h.insert_opportunity(db, org_b, pipe_b, stages_b["open"])
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/tasks",
        json={"title": "Cross-tenant", "opportunity_id": opp_b},
        headers=_headers(h.make_token(org_a, user_a)),
    )
    assert resp.status_code == 404, resp.text
