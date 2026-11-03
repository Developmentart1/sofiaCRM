"""ARM module tests - prompt construction, tenant isolation, RBAC, LLM failure."""

import modules.arm.llm as arm_llm
from core.database import SessionLocal

import helpers as h


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_contact_with_activity() -> tuple[str, str, str]:
    db = SessionLocal()
    org = h.insert_org(db, "ARM Org")
    user = h.insert_user(db, org, role="admin")
    contact = h.insert_contact(db, org, first_name="Laura")
    h.insert_activity(db, org, user, type_="meeting", contact_id=contact)
    db.commit()
    db.close()
    return org, user, contact


def test_draft_followup_prompt_includes_contact_and_activities(client, monkeypatch):
    org, user, contact = _seed_contact_with_activity()
    captured: dict[str, str] = {}

    def fake_complete(system: str, user_text: str) -> str:
        captured["system"] = system
        captured["user"] = user_text
        return "MENSAJE DE SEGUIMIENTO"

    monkeypatch.setattr(arm_llm, "complete", fake_complete)

    resp = client.post(
        f"/api/v1/arm/contacts/{contact}/draft-followup",
        headers=_headers(h.make_token(org, user)),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["text"] == "MENSAJE DE SEGUIMIENTO"
    assert "Laura" in captured["user"]
    assert "meeting" in captured["user"]


def test_summarize_relation_isolates_tenant(client, monkeypatch):
    db = SessionLocal()
    org_a = h.insert_org(db, "ARM A")
    org_b = h.insert_org(db, "ARM B")
    user_a = h.insert_user(db, org_a, role="admin")
    h.insert_user(db, org_b, role="admin")
    contact_b = h.insert_contact(db, org_b, first_name="Otra")
    db.commit()
    db.close()

    def fake_complete(system: str, user_text: str) -> str:
        raise AssertionError("LLM no debe llamarse para contacto de otra organizacion")

    monkeypatch.setattr(arm_llm, "complete", fake_complete)

    resp = client.post(
        f"/api/v1/arm/contacts/{contact_b}/summarize",
        headers=_headers(h.make_token(org_a, user_a)),
    )
    assert resp.status_code == 404, resp.text


def test_arm_rbac_requires_permission(client, monkeypatch):
    db = SessionLocal()
    org = h.insert_org(db, "ARM RBAC")
    user = h.insert_user(db, org, role="guest")
    contact = h.insert_contact(db, org, first_name="Laura")
    db.commit()
    db.close()

    def fake_complete(system: str, user_text: str) -> str:
        return "NUNCA"

    monkeypatch.setattr(arm_llm, "complete", fake_complete)

    resp = client.post(
        f"/api/v1/arm/contacts/{contact}/draft-followup",
        headers=_headers(h.make_token(org, user, role="guest")),
    )
    assert resp.status_code == 403, resp.text


def test_llm_failure_maps_to_domain_error(client, monkeypatch):
    org, user, contact = _seed_contact_with_activity()

    def fake_complete(system: str, user_text: str) -> str:
        raise RuntimeError("mimo no disponible")

    monkeypatch.setattr(arm_llm, "complete", fake_complete)

    resp = client.post(
        f"/api/v1/arm/contacts/{contact}/draft-followup",
        headers=_headers(h.make_token(org, user)),
    )
    assert resp.status_code == 502, resp.text
    assert resp.json()["error"]["code"] == "arm_llm_error"
