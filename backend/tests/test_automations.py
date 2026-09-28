"""Automation module tests — triggers, conditions, anti-recursion, tenant
isolation, RBAC and dry-run non-persistence."""
from core.database import SessionLocal

import helpers as h


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_org_user(db, name: str = "Org", role: str = "admin") -> tuple[str, str]:
    org = h.insert_org(db, name)
    user = h.insert_user(db, org, role=role)
    db.commit()
    return org, user


def test_rule_stage_changed_creates_task(client):
    db = SessionLocal()
    org, user = _seed_org_user(db)
    contact = h.insert_contact(db, org)
    pipe, stages = h.insert_pipeline_and_stages(db, org)
    opp = h.insert_opportunity(db, org, pipe, stages["open"], contact_id=contact, assigned_user_id=user)
    db.commit()
    db.close()

    token = h.make_token(org, user)
    headers = _headers(token)

    resp = client.post(
        "/api/v1/automations/rules",
        json={
            "name": "Seguimiento al ganar",
            "trigger_event": "opportunity.stage_changed",
            "actions": [{"action_type": "create_task", "config": {"title": "Seguimiento", "priority": "high"}}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    tr = client.post(f"/api/v1/opportunities/{opp}/transition", json={"stage_id": stages["won"]}, headers=headers)
    assert tr.status_code == 200, tr.text

    tasks = client.get("/api/v1/tasks", params={"opportunity_id": opp}, headers=headers).json()["items"]
    assert any(t["title"] == "Seguimiento" for t in tasks), tasks

    execs = client.get("/api/v1/automations/executions", headers=headers).json()["items"]
    assert any(e["status"] == "success" for e in execs), execs


def test_condition_not_matched_skips_execution(client):
    db = SessionLocal()
    org, user = _seed_org_user(db)
    pipe, stages = h.insert_pipeline_and_stages(db, org)
    opp = h.insert_opportunity(db, org, pipe, stages["open"], assigned_user_id=user)
    db.commit()
    db.close()

    token = h.make_token(org, user)
    headers = _headers(token)

    resp = client.post(
        "/api/v1/automations/rules",
        json={
            "name": "Solo si pasa a lost",
            "trigger_event": "opportunity.stage_changed",
            "conditions": [{"field": "to_stage_id", "op": "eq", "value": stages["lost"]}],
            "actions": [{"action_type": "create_task", "config": {"title": "No debe crearse"}}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    tr = client.post(f"/api/v1/opportunities/{opp}/transition", json={"stage_id": stages["won"]}, headers=headers)
    assert tr.status_code == 200, tr.text

    execs = client.get("/api/v1/automations/executions", headers=headers).json()["items"]
    assert any(e["status"] == "skipped" and e["result"].get("reason") == "conditions_not_met" for e in execs), execs

    tasks = client.get("/api/v1/tasks", params={"opportunity_id": opp}, headers=headers).json()["items"]
    assert not any(t["title"] == "No debe crearse" for t in tasks)


def test_anti_recursion_bounded_depth(client):
    db = SessionLocal()
    org, user = _seed_org_user(db)
    db.commit()
    db.close()

    token = h.make_token(org, user)
    headers = _headers(token)

    resp = client.post(
        "/api/v1/automations/rules",
        json={
            "name": "Tarea en cascada",
            "trigger_event": "task.created",
            "max_depth": 5,
            "actions": [{"action_type": "create_task", "config": {"title": "Cascada"}}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    created = client.post("/api/v1/tasks", json={"title": "Original"}, headers=headers)
    assert created.status_code == 201, created.text

    execs = client.get("/api/v1/automations/executions", headers=headers).json()["items"]
    assert len(execs) <= 5, execs
    assert all(e["depth"] <= 5 for e in execs), execs


def test_cycle_between_two_rules_is_broken(client):
    db = SessionLocal()
    org, user = _seed_org_user(db)
    db.commit()
    db.close()

    token = h.make_token(org, user)
    headers = _headers(token)

    a = client.post(
        "/api/v1/automations/rules",
        json={
            "name": "A",
            "trigger_event": "task.created",
            "actions": [{"action_type": "create_activity", "config": {"type": "note", "subject": "A"}}],
        },
        headers=headers,
    )
    assert a.status_code == 201, a.text

    b = client.post(
        "/api/v1/automations/rules",
        json={
            "name": "B",
            "trigger_event": "activity.created",
            "actions": [{"action_type": "create_task", "config": {"title": "B"}}],
        },
        headers=headers,
    )
    assert b.status_code == 201, b.text

    created = client.post("/api/v1/tasks", json={"title": "Original"}, headers=headers)
    assert created.status_code == 201, created.text

    execs = client.get("/api/v1/automations/executions", headers=headers).json()["items"]
    assert len(execs) <= 6, execs
    assert any(e["status"] == "skipped" and e["result"].get("reason") == "cycle" for e in execs), execs


def test_move_stage_invalid_marks_failed_and_keeps_opportunity(client):
    db = SessionLocal()
    org, user = _seed_org_user(db)
    pipe, stages = h.insert_pipeline_and_stages(db, org)
    opp = h.insert_opportunity(db, org, pipe, stages["open"], assigned_user_id=user)
    db.commit()
    db.close()

    token = h.make_token(org, user)
    headers = _headers(token)

    resp = client.post(
        "/api/v1/automations/rules",
        json={
            "name": "Mover a open (fallará tras ganar)",
            "trigger_event": "opportunity.stage_changed",
            "actions": [{"action_type": "move_stage", "config": {"stage_id": stages["open"]}}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    tr = client.post(f"/api/v1/opportunities/{opp}/transition", json={"stage_id": stages["won"]}, headers=headers)
    assert tr.status_code == 200, tr.text

    execs = client.get("/api/v1/automations/executions", headers=headers).json()["items"]
    assert any(e["status"] == "failed" for e in execs), execs

    opp_read = client.get(f"/api/v1/opportunities/{opp}", headers=headers).json()
    assert opp_read["status"] == "won"


def test_tenant_isolation_rule_does_not_fire_cross_org(client):
    db = SessionLocal()
    org_a, user_a = _seed_org_user(db, "Org A")
    org_b, user_b = _seed_org_user(db, "Org B")
    pipe_a, stages_a = h.insert_pipeline_and_stages(db, org_a)
    opp_a = h.insert_opportunity(db, org_a, pipe_a, stages_a["open"], assigned_user_id=user_a)
    pipe_b, stages_b = h.insert_pipeline_and_stages(db, org_b)
    opp_b = h.insert_opportunity(db, org_b, pipe_b, stages_b["open"], assigned_user_id=user_b)
    db.commit()
    db.close()

    token_a = h.make_token(org_a, user_a)
    token_b = h.make_token(org_b, user_b)
    headers_a = _headers(token_a)
    headers_b = _headers(token_b)

    resp = client.post(
        "/api/v1/automations/rules",
        json={
            "name": "Regla de org A",
            "trigger_event": "opportunity.stage_changed",
            "actions": [{"action_type": "create_task", "config": {"title": "Solo en A"}}],
        },
        headers=headers_a,
    )
    assert resp.status_code == 201, resp.text

    tr = client.post(f"/api/v1/opportunities/{opp_b}/transition", json={"stage_id": stages_b["won"]}, headers=headers_b)
    assert tr.status_code == 200, tr.text

    execs_b = client.get("/api/v1/automations/executions", headers=headers_b).json()["items"]
    assert execs_b == [], execs_b

    tasks_a = client.get("/api/v1/tasks", params={"opportunity_id": opp_a}, headers=headers_a).json()["items"]
    assert not any(t["title"] == "Solo en A" for t in tasks_a)


def test_create_rule_denied_for_role_without_permission(client):
    db = SessionLocal()
    org, user = _seed_org_user(db, role="asesor")
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/automations/rules",
        json={"name": "No permitida", "trigger_event": "task.created", "actions": []},
        headers=_headers(h.make_token(org, user, role="asesor")),
    )
    assert resp.status_code == 403, resp.text


def test_dry_run_does_not_persist(client):
    db = SessionLocal()
    org, user = _seed_org_user(db)
    pipe, stages = h.insert_pipeline_and_stages(db, org)
    opp = h.insert_opportunity(db, org, pipe, stages["open"], assigned_user_id=user)
    db.commit()
    db.close()

    token = h.make_token(org, user)
    headers = _headers(token)

    rule = client.post(
        "/api/v1/automations/rules",
        json={
            "name": "Dry run",
            "trigger_event": "opportunity.stage_changed",
            "actions": [{"action_type": "create_task", "config": {"title": "Debería no persistir"}}],
        },
        headers=headers,
    ).json()

    from datetime import datetime, timezone
    resp = client.post(
        f"/api/v1/automations/rules/{rule['id']}/test",
        json={
            "event_type": "opportunity.stage_changed",
            "payload": {
                "opportunity_id": opp,
                "from_stage_id": stages["open"],
                "to_stage_id": stages["won"],
                "entered_stage_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["matched"] is True
    assert body["status"] == "success"

    tasks = client.get("/api/v1/tasks", params={"opportunity_id": opp}, headers=headers).json()["items"]
    assert not any(t["title"] == "Debería no persistir" for t in tasks), tasks

    execs = client.get("/api/v1/automations/executions", headers=headers).json()["items"]
    assert execs == [], execs
