"""Activity module tests — manual create/delete, filters, system activities."""
from core.database import SessionLocal

import helpers as h


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_note_activity(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/activities",
        json={"type": "note", "subject": "Llamada de seguimiento"},
        headers=_headers(h.make_token(org, user)),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["type"] == "note"
    assert data["subject"] == "Llamada de seguimiento"
    assert data["user_id"] == user


def test_list_activities_filtered_by_type(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()
    token = h.make_token(org, user)
    headers = _headers(token)

    client.post("/api/v1/activities", json={"type": "note", "subject": "Nota"}, headers=headers)
    client.post("/api/v1/activities", json={"type": "call", "subject": "Llamada"}, headers=headers)

    resp = client.get("/api/v1/activities", params={"type": "note"}, headers=headers)
    assert resp.status_code == 200, resp.text
    types = [a["type"] for a in resp.json()["items"]]
    assert types == ["note"]


def test_delete_manual_activity_allowed(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()
    token = h.make_token(org, user)
    headers = _headers(token)

    activity_id = client.post(
        "/api/v1/activities", json={"type": "note", "subject": "Borrable"}, headers=headers
    ).json()["id"]

    resp = client.delete(f"/api/v1/activities/{activity_id}", headers=headers)
    assert resp.status_code == 204, resp.text


def test_delete_system_activity_forbidden(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    activity_id = h.insert_activity(db, org, user, type_="stage_change")
    db.commit()
    db.close()

    resp = client.delete(
        f"/api/v1/activities/{activity_id}", headers=_headers(h.make_token(org, user))
    )
    assert resp.status_code == 403, resp.text


def test_create_system_activity_forbidden(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/activities",
        json={"type": "stage_change", "subject": "No permitido"},
        headers=_headers(h.make_token(org, user)),
    )
    assert resp.status_code == 422, resp.text


def test_stage_change_generates_activity(client):
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role="admin")
    contact = h.insert_contact(db, org)
    pipe, stages = h.insert_pipeline_and_stages(db, org)
    opp = h.insert_opportunity(db, org, pipe, stages["open"], contact_id=contact, assigned_user_id=user)
    db.commit()
    db.close()
    token = h.make_token(org, user)
    headers = _headers(token)

    resp = client.post(
        f"/api/v1/opportunities/{opp}/transition",
        json={"stage_id": stages["won"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    resp = client.get(
        "/api/v1/activities", params={"opportunity_id": opp}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert any(a["type"] == "stage_change" for a in items)
