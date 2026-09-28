"""Fase 0 smoke test — end-to-end flow against a TEMPORARY SQLite database.

Flow: bootstrap org → login (assert cookie set) → cookie-only auth check →
create contact → pipeline + stages → opportunity → stage transition →
verify event_outbox has rows.

Never touches the project's real .db. Run from backend/: python scripts/smoke.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SRC = BACKEND / "src"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(SRC))

# Point the app at a temporary SQLite DB BEFORE importing any app module.
_tmpdir = tempfile.mkdtemp(prefix="crm_splash_smoke_")
_tmp_db = os.path.join(_tmpdir, "smoke.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["ENV"] = "test"
os.environ["STORAGE_ROOT"] = os.path.join(_tmpdir, "storage")

import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core.database import SessionLocal  # noqa: E402
from src.main import app  # noqa: E402


def fail(msg: str) -> None:
    print(f"SMOKE FAIL: {msg}")
    sys.exit(1)


def _apply_migrations(db_path: str) -> None:
    """Create the full schema in the temp DB using the real Alembic migration.

    create_all() is not enough here: the `opportunities.source_id` FK targets
    `lead_sources`, which has no ORM model (only exists in the migration).
    """
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")


def main() -> None:
    _apply_migrations(_tmp_db)

    org_slug = "smoke-demo"
    email = "admin@smoke.mx"
    password = "Smoke1234!"

    with TestClient(app) as client:
        # 1. Bootstrap org (creates the first admin user)
        resp = client.post(
            "/api/v1/organizations/bootstrap",
            json={
                "name": "Smoke Org",
                "slug": org_slug,
                "timezone": "America/Mexico_City",
                "currency": "MXN",
                "locale": "es-MX",
                "admin_email": email,
                "admin_password": password,
                "admin_full_name": "Smoke Admin",
            },
        )
        if resp.status_code != 201:
            fail(f"bootstrap returned {resp.status_code}: {resp.text}")

        # 2. Login — assert the access_token cookie is set on the response
        resp = client.post(
            "/api/v1/users/login",
            json={"organization_slug": org_slug, "email": email, "password": password},
        )
        if resp.status_code != 200:
            fail(f"login returned {resp.status_code}: {resp.text}")
        body = resp.json()
        if not body.get("access_token"):
            fail("login response missing access_token")
        set_cookie = resp.headers.get("set-cookie", "")
        if "access_token=" not in set_cookie:
            fail("login response did not set the access_token cookie")
        token = body["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        admin_user_id = body["user"]["id"]

        # 3. Cookie-only auth check (no Authorization header)
        resp = client.get("/api/v1/contacts")
        if resp.status_code != 200:
            fail(f"cookie-only auth failed on GET /contacts: {resp.status_code}: {resp.text}")

        # 4. Create contact
        resp = client.post(
            "/api/v1/contacts",
            json={"first_name": "Smoke", "last_name": "Contact", "email": "contact@smoke.mx"},
            headers=headers,
        )
        if resp.status_code != 201:
            fail(f"create contact returned {resp.status_code}: {resp.text}")
        contact_id = resp.json()["id"]

        # 5. Pipeline + stages
        resp = client.post("/api/v1/pipelines", json={"name": "Smoke Pipeline"}, headers=headers)
        if resp.status_code != 201:
            fail(f"create pipeline returned {resp.status_code}: {resp.text}")
        pipeline_id = resp.json()["id"]

        stage_ids: dict[str, str] = {}
        for name, stype, pos in [("Open", "open", 1), ("Won", "won", 2), ("Lost", "lost", 3)]:
            resp = client.post(
                f"/api/v1/pipelines/{pipeline_id}/stages",
                json={
                    "name": name,
                    "stage_type": stype,
                    "probability": 100 if stype == "won" else (20 if stype == "open" else 0),
                    "position": pos,
                },
                headers=headers,
            )
            if resp.status_code != 201:
                fail(f"create stage {name} returned {resp.status_code}: {resp.text}")
            stage_ids[stype] = resp.json()["id"]

        # 6. Opportunity
        resp = client.post(
            "/api/v1/opportunities",
            json={
                "pipeline_id": pipeline_id,
                "stage_id": stage_ids["open"],
                "name": "Smoke Opportunity",
                "estimated_value": 10000,
                "contact_id": contact_id,
            },
            headers=headers,
        )
        if resp.status_code != 201:
            fail(f"create opportunity returned {resp.status_code}: {resp.text}")
        opp_id = resp.json()["id"]

        # 6b. Create a task linked to the opportunity
        resp = client.post(
            "/api/v1/tasks",
            json={"title": "Smoke Task", "opportunity_id": opp_id},
            headers=headers,
        )
        if resp.status_code != 201:
            fail(f"create task returned {resp.status_code}: {resp.text}")
        task_id = resp.json()["id"]

        # 6c. Complete the task (idempotent PATCH status=completed)
        resp = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "completed"}, headers=headers)
        if resp.status_code != 200 or resp.json()["status"] != "completed":
            fail(f"complete task returned {resp.status_code}: {resp.text}")

        # 6d. Create a manual note activity
        resp = client.post(
            "/api/v1/activities",
            json={"type": "note", "subject": "Smoke Note", "opportunity_id": opp_id},
            headers=headers,
        )
        if resp.status_code != 201:
            fail(f"create activity returned {resp.status_code}: {resp.text}")

        # 7. Stage transition → won
        # 6e. Create automation rule: "al ganar oportunidad → crear tarea de seguimiento"
        resp = client.post(
            "/api/v1/automations/rules",
            json={
                "name": "Seguimiento al ganar",
                "trigger_event": "opportunity.won",
                "actions": [
                    {
                        "action_type": "create_task",
                        "config": {
                            "title": "Seguimiento post-venta",
                            "assigned_user_id": admin_user_id,
                            "due_offset_days": 7,
                        },
                    }
                ],
            },
            headers=headers,
        )
        if resp.status_code != 201:
            fail(f"create automation rule returned {resp.status_code}: {resp.text}")
        rule_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/opportunities/{opp_id}/transition",
            json={"stage_id": stage_ids["won"]},
            headers=headers,
        )
        if resp.status_code != 200:
            fail(f"transition returned {resp.status_code}: {resp.text}")

        # 7b. Verify the automation created the follow-up task and recorded success
        resp = client.get("/api/v1/tasks", params={"opportunity_id": opp_id}, headers=headers)
        if resp.status_code != 200:
            fail(f"list tasks returned {resp.status_code}: {resp.text}")
        task_titles = [t.get("title") for t in resp.json().get("items", [])]
        if "Seguimiento post-venta" not in task_titles:
            fail(f"automation task missing; got titles {task_titles}")

        resp = client.get("/api/v1/automations/executions", params={"rule_id": rule_id}, headers=headers)
        if resp.status_code != 200:
            fail(f"list executions returned {resp.status_code}: {resp.text}")
        exec_statuses = [e.get("status") for e in resp.json().get("items", [])]
        if "success" not in exec_statuses:
            fail(f"automation execution not success; got {exec_statuses}")

        # 7b. Verify the stage_change activity was recorded automatically
        resp = client.get("/api/v1/activities", params={"opportunity_id": opp_id}, headers=headers)
        if resp.status_code != 200:
            fail(f"list activities returned {resp.status_code}: {resp.text}")
        activity_types = [a.get("type") for a in resp.json().get("items", [])]
        if "stage_change" not in activity_types:
            fail(f"stage_change activity missing; got types {activity_types}")

        # 7c. Documents: upload (direct /api) → list → download by both routes
        doc_bytes = b"documento-de-prueba"
        resp = client.post(
            "/api/documents",
            files={"file": ("smoke.txt", doc_bytes, "text/plain")},
            data={"folder": "smoke", "opportunity_id": opp_id},
            headers=headers,
        )
        if resp.status_code != 201:
            fail(f"upload document returned {resp.status_code}: {resp.text}")
        doc_id = resp.json()["id"]

        resp = client.get("/api/v1/documents", headers=headers)
        if resp.status_code != 200:
            fail(f"list documents returned {resp.status_code}: {resp.text}")
        doc_ids = [d.get("id") for d in resp.json().get("items", [])]
        if doc_id not in doc_ids:
            fail(f"uploaded document missing from list; got {doc_ids}")

        for url in (f"/api/documents/{doc_id}/download", f"/api/v1/documents/{doc_id}/download"):
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                fail(f"download {url} returned {resp.status_code}: {resp.text}")
            if resp.content != doc_bytes:
                fail(f"download {url} content mismatch: {resp.content!r}")

        # 7d. Reports: KPIs with full structure
        resp = client.get("/api/v1/reports/kpis", headers=headers)
        if resp.status_code != 200:
            fail(f"kpis returned {resp.status_code}: {resp.text}")
        kpis = resp.json()
        expected_keys = {
            "total_contacts", "total_companies", "total_opportunities",
            "open_opportunities_value", "won_opportunities_value",
            "won_opportunities_count", "lost_opportunities_count",
            "conversion_rate", "average_deal_size", "pipeline_velocity",
            "overdue_tasks", "tasks_due_today", "contacts_added_this_month",
            "opportunities_won_this_month",
        }
        missing = expected_keys - set(kpis.keys())
        if missing:
            fail(f"kpis missing keys: {sorted(missing)}")

    # 8. Verify event_outbox has rows
    db = SessionLocal()
    try:
        n = db.execute(sa.text("SELECT COUNT(*) FROM event_outbox")).scalar_one()
    finally:
        db.close()
    if n == 0:
        fail("event_outbox has no rows")

    print(f"SMOKE OK (event_outbox rows: {n})")


if __name__ == "__main__":
    main()
