"""RBAC matrix tests — role × endpoint permission matrix + tenant isolation.

Builds a parametrized matrix over the real roles from ``core/rbac.py``
(admin, director, gerente, asesor, operaciones) and the key endpoints of each
module. Asserts:

- the most privileged role(s) can perform each operation;
- the least privileged role(s) get 403 on management operations
  (create automation rules, create users, create pipelines, ...);
- every endpoint returns 401 with no credentials at all.

Plus two API-level tenant isolation cases: a user of Org B with a valid token
can neither see nor modify Org A's data.
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from uuid import uuid4

import helpers as h
import pytest

from core.database import SessionLocal

ROLES = ["admin", "director", "gerente", "asesor", "operaciones"]

# role → expected status for each management/read endpoint.
MATRIX = {
    "create_rule": {
        "method": "POST",
        "path": "/api/v1/automations/rules",
        "payload": {"name": "R", "trigger_event": "task.created", "actions": []},
        "expect": {"admin": 201, "director": 201, "gerente": 403, "asesor": 403, "operaciones": 403},
    },
    "create_user": {
        "method": "POST",
        "path": "/api/v1/users",
        "payload": {"email": "u@rbac.mx", "full_name": "User RBAC", "password": "password123"},
        "expect": {"admin": 201, "director": 403, "gerente": 403, "asesor": 403, "operaciones": 403},
    },
    "create_contact": {
        "method": "POST",
        "path": "/api/v1/contacts",
        "payload": {"first_name": "C", "last_name": "L"},
        "expect": {"admin": 201, "director": 201, "gerente": 201, "asesor": 201, "operaciones": 403},
    },
    "create_opportunity": {
        "method": "POST",
        "path": "/api/v1/opportunities",
        "payload": None,  # filled with per-test stage ids
        "expect": {"admin": 201, "director": 201, "gerente": 201, "asesor": 201, "operaciones": 403},
    },
    "create_pipeline": {
        "method": "POST",
        "path": "/api/v1/pipelines",
        "payload": {"name": "P"},
        "expect": {"admin": 201, "director": 201, "gerente": 403, "asesor": 403, "operaciones": 403},
    },
    "read_kpis": {
        "method": "GET",
        "path": "/api/v1/reports/kpis",
        "payload": None,
        "expect": {"admin": 200, "director": 200, "gerente": 200, "asesor": 200, "operaciones": 200},
    },
}

MATRIX_CASES = [
    pytest.param(name, role, id=f"{name}-{role}")
    for name in MATRIX
    for role in ROLES
]


def _seed_user(role: str) -> dict[str, str]:
    db = SessionLocal()
    org = h.insert_org(db, f"RBAC {role} {uuid4().hex[:6]}")
    user = h.insert_user(db, org, role=role)
    pipe, stages = h.insert_pipeline_and_stages(db, org)
    db.commit()
    db.close()
    token = h.make_token(org, user, role=role)
    return {"org": org, "user": user, "role": role, "token": token,
            "pipeline": pipe, "stages": stages}


@pytest.mark.parametrize("name,role", MATRIX_CASES)
def test_rbac_matrix(client, name, role):
    case = MATRIX[name]
    ctx = _seed_user(role)
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    payload = case["payload"]
    if name == "create_opportunity":
        payload = {
            "pipeline_id": ctx["pipeline"],
            "stage_id": ctx["stages"]["open"],
            "name": "Opp",
        }

    resp = client.request(case["method"], case["path"], json=payload, headers=headers)
    expected = case["expect"][role]
    assert resp.status_code == expected, (
        f"{name} as {role}: expected {expected}, got {resp.status_code}: {resp.text}"
    )


UNAUTH_CASES = [
    pytest.param("GET", "/api/v1/contacts", None, id="unauth-contacts"),
    pytest.param("GET", "/api/v1/reports/kpis", None, id="unauth-kpis"),
    pytest.param("POST", "/api/v1/contacts", {"first_name": "A", "last_name": "B"}, id="unauth-contact-create"),
    pytest.param(
        "POST", "/api/v1/automations/rules",
        {"name": "R", "trigger_event": "task.created", "actions": []},
        id="unauth-rule-create",
    ),
    pytest.param(
        "POST", "/api/v1/users",
        {"email": "x@y.mx", "full_name": "X Y", "password": "password123"},
        id="unauth-user-create",
    ),
    pytest.param("POST", "/api/v1/pipelines", {"name": "P"}, id="unauth-pipeline-create"),
]


@pytest.mark.parametrize("method,path,payload", UNAUTH_CASES)
def test_all_roles_401_without_auth(client, method, path, payload):
    resp = client.request(method, path, json=payload)
    assert resp.status_code == 401, f"{method} {path}: expected 401, got {resp.status_code}: {resp.text}"


def test_org_isolation_list_and_get(client):
    db = SessionLocal()
    org_a = h.insert_org(db, "Iso A")
    org_b = h.insert_org(db, "Iso B")
    h.insert_user(db, org_a, role="admin")
    user_b = h.insert_user(db, org_b, role="admin")
    contact_a = h.insert_contact(db, org_a, first_name="SecretA")
    db.commit()
    db.close()

    headers_b = {"Authorization": f"Bearer {h.make_token(org_b, user_b)}"}

    # List: Org B's user must never see Org A's contact.
    resp = client.get("/api/v1/contacts", headers=headers_b)
    assert resp.status_code == 200, resp.text
    assert all(c["organization_id"] == org_b for c in resp.json()), resp.json()

    # Direct read of Org A's contact id → 404 (not 200/403).
    resp = client.get(f"/api/v1/contacts/{contact_a}", headers=headers_b)
    assert resp.status_code == 404, resp.text


def test_org_isolation_write_denied(client):
    db = SessionLocal()
    org_a = h.insert_org(db, "Iso A2")
    org_b = h.insert_org(db, "Iso B2")
    h.insert_user(db, org_a, role="admin")
    user_b = h.insert_user(db, org_b, role="admin")
    contact_a = h.insert_contact(db, org_a, first_name="SecretA2")
    db.commit()
    db.close()

    headers_b = {"Authorization": f"Bearer {h.make_token(org_b, user_b)}"}

    resp = client.patch(
        f"/api/v1/contacts/{contact_a}",
        json={"first_name": "Hacked"},
        headers=headers_b,
    )
    assert resp.status_code == 404, resp.text


def test_invalid_role_is_denied():
    """Un rol inexistente debe retornar False y lanzar ForbiddenError."""
    from core.rbac import role_has, require_permission, Permission, ForbiddenError

    assert role_has("rol_inexistente", Permission.CONTACT_READ) is False
    with pytest.raises(ForbiddenError):
        require_permission("rol_inexistente", Permission.CONTACT_READ)
