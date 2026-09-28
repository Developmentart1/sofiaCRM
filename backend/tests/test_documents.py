"""Document module tests — upload/download roundtrip, tenant isolation,
soft delete, size limit and folder filter."""
from core.config import get_settings
from core.database import SessionLocal

import helpers as h


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_org_user(role: str = "admin") -> tuple[str, str, str]:
    db = SessionLocal()
    org = h.insert_org(db)
    user = h.insert_user(db, org, role=role)
    db.commit()
    db.close()
    return org, user, h.make_token(org, user, role=role)


def test_upload_download_roundtrip_both_prefixes(client):
    org, user, token = _seed_org_user()
    headers = _headers(token)

    # Upload via the direct (no /v1) route the frontend uses.
    resp = client.post(
        "/api/documents",
        files={"file": ("report.txt", b"hola mundo", "text/plain")},
        data={"folder": "ventas"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    assert doc["name"] == "report.txt"
    assert doc["size"] == len(b"hola mundo")
    assert doc["folder"] == "ventas"
    assert doc["uploaded_by_id"] == user

    # List via /api/v1 (rewrite path).
    listed = client.get("/api/v1/documents", headers=headers)
    assert listed.status_code == 200, listed.text
    names = [d["name"] for d in listed.json()["items"]]
    assert "report.txt" in names

    # Download via direct /api and via /api/v1 — content must match both.
    direct = client.get(f"/api/documents/{doc['id']}/download", headers=headers)
    assert direct.status_code == 200, direct.text
    assert direct.content == b"hola mundo"

    v1 = client.get(f"/api/v1/documents/{doc['id']}/download", headers=headers)
    assert v1.status_code == 200, v1.text
    assert v1.content == b"hola mundo"


def test_download_tenant_isolation(client):
    org_a, user_a, token_a = _seed_org_user()
    org_b, user_b, token_b = _seed_org_user()

    doc = client.post(
        "/api/documents",
        files={"file": ("secret.txt", b"org-a-only", "text/plain")},
        headers=_headers(token_a),
    ).json()

    # Org B cannot download (or see) Org A's document, even with a valid id.
    resp = client.get(f"/api/documents/{doc['id']}/download", headers=_headers(token_b))
    assert resp.status_code == 404, resp.text

    listed = client.get("/api/v1/documents", headers=_headers(token_b))
    assert doc["id"] not in [d["id"] for d in listed.json()["items"]]


def test_soft_delete_hides_and_blocks_download(client):
    org, user, token = _seed_org_user()
    headers = _headers(token)

    doc = client.post(
        "/api/documents",
        files={"file": ("gone.txt", b"delete me", "text/plain")},
        headers=headers,
    ).json()

    resp = client.delete(f"/api/v1/documents/{doc['id']}", headers=headers)
    assert resp.status_code == 204, resp.text

    listed = client.get("/api/v1/documents", headers=headers)
    assert doc["id"] not in [d["id"] for d in listed.json()["items"]]

    download = client.get(f"/api/documents/{doc['id']}/download", headers=headers)
    assert download.status_code == 404, download.text


def test_upload_size_limit(client, monkeypatch):
    org, user, token = _seed_org_user()
    monkeypatch.setattr(get_settings(), "max_upload_size_bytes", 20)

    resp = client.post(
        "/api/documents",
        files={"file": ("big.txt", b"x" * 200, "text/plain")},
        headers=_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert "maximum size" in resp.text


def test_upload_rejects_cross_tenant_contact(client):
    org_a, user_a, token_a = _seed_org_user()
    db = SessionLocal()
    org_b = h.insert_org(db, "Org B")
    contact_b = h.insert_contact(db, org_b, "Other")
    db.commit()
    db.close()

    resp = client.post(
        "/api/documents",
        files={"file": ("c.txt", b"data", "text/plain")},
        data={"contact_id": contact_b},
        headers=_headers(token_a),
    )
    assert resp.status_code == 404, resp.text


def test_list_filters_by_folder_and_search(client):
    org, user, token = _seed_org_user()
    headers = _headers(token)

    client.post("/api/documents", files={"file": ("a.txt", b"1", "text/plain")}, data={"folder": "inbox"}, headers=headers)
    client.post("/api/documents", files={"file": ("b.txt", b"2", "text/plain")}, data={"folder": "archivo"}, headers=headers)

    inbox = client.get("/api/v1/documents", params={"folder": "inbox"}, headers=headers)
    names = [d["name"] for d in inbox.json()["items"]]
    assert names == ["a.txt"]

    search = client.get("/api/v1/documents", params={"search": "b"}, headers=headers)
    s_names = [d["name"] for d in search.json()["items"]]
    assert s_names == ["b.txt"]
