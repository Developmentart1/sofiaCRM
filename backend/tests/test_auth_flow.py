"""Auth flow tests — login, HttpOnly cookie, logout, password change, expiry.

These exercise the REAL auth path (``/api/v1/users/login`` sets the
``access_token`` cookie, ``get_current_user`` reads it from the cookie when no
Authorization header is present, and ``/api/v1/users/me/password`` changes the
password). Data is seeded per-test with unique org slugs/emails so nothing
collides in the shared temporary test DB.
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from core.database import SessionLocal
from core.security import create_access_token, hash_password

PASSWORD = "Password123!"
WRONG = "WrongPassword123!"
NEW = "NewPassword123!"


def _seed(
    db,
    *,
    email: str | None = None,
    role: str = "admin",
    is_active: bool = True,
) -> dict[str, str]:
    org_id = str(uuid4())
    user_id = str(uuid4())
    slug = f"auth-{uuid4().hex[:8]}"
    email = email or f"{uuid4().hex[:8]}@auth.mx"
    now = datetime.now(UTC)
    db.execute(
        sa.text(
            "INSERT INTO organizations (id, name, slug, created_at, updated_at) "
            "VALUES (:i, :n, :s, :t, :t)"
        ),
        {"i": org_id, "n": "Auth Org", "s": slug, "t": now},
    )
    db.execute(
        sa.text(
            "INSERT INTO users (id, organization_id, email, email_normalized, full_name, "
            "password_hash, role, is_active, created_at, updated_at) "
            "VALUES (:i, :o, :e, :en, :n, :p, :r, :active, :t, :t)"
        ),
        {
            "i": user_id, "o": org_id, "e": email, "en": email.lower(), "n": "Auth User",
            "p": hash_password(PASSWORD), "r": role, "active": is_active, "t": now,
        },
    )
    db.commit()
    return {"org_id": org_id, "user_id": user_id, "slug": slug, "email": email, "role": role}


def _login(client, ctx: dict[str, str], password: str = PASSWORD):
    return client.post(
        "/api/v1/users/login",
        json={"organization_slug": ctx["slug"], "email": ctx["email"], "password": password},
    )


def test_login_valid_sets_httponly_cookie(client):
    db = SessionLocal()
    ctx = _seed(db)
    db.close()

    resp = _login(client, ctx)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("access_token"), body
    assert body.get("token_type") == "bearer"
    assert body["user"]["id"] == ctx["user_id"]

    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie, set_cookie
    assert "httponly" in set_cookie.lower(), set_cookie
    assert "samesite=lax" in set_cookie.lower(), set_cookie


def test_login_wrong_password_401_no_cookie(client):
    db = SessionLocal()
    ctx = _seed(db)
    db.close()

    resp = _login(client, ctx, password=WRONG)
    assert resp.status_code == 401, resp.text
    assert "access_token=" not in resp.headers.get("set-cookie", "")


def test_cookie_only_auth_no_authorization_header(client):
    db = SessionLocal()
    ctx = _seed(db)
    db.close()

    resp = _login(client, ctx)
    assert resp.status_code == 200, resp.text

    # No Authorization header — the cookie alone must authenticate.
    resp = client.get("/api/v1/contacts")
    assert resp.status_code == 200, resp.text


def test_missing_cookie_and_header_401(client):
    resp = client.get("/api/v1/contacts")
    assert resp.status_code == 401, resp.text


def test_expired_token_401(client):
    db = SessionLocal()
    ctx = _seed(db)
    db.close()

    expired = create_access_token(
        subject=ctx["user_id"],
        organization_id=ctx["org_id"],
        role=ctx["role"],
        expires_minutes=-1,
    )
    resp = client.get("/api/v1/contacts", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401, resp.text


def test_logout_clears_cookie(client):
    db = SessionLocal()
    ctx = _seed(db)
    db.close()

    assert _login(client, ctx).status_code == 200

    resp = client.post("/api/v1/users/logout")
    assert resp.status_code == 200, resp.text
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie, set_cookie
    lowered = set_cookie.lower()
    assert "max-age=0" in lowered or "1970" in set_cookie, set_cookie

    # After logout the cookie is gone from the client jar → protected route is 401.
    resp = client.get("/api/v1/contacts")
    assert resp.status_code == 401, resp.text


def test_change_password_wrong_then_correct(client):
    db = SessionLocal()
    ctx = _seed(db)
    db.close()

    login = _login(client, ctx)
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    # Wrong current password → error, no change.
    resp = client.post(
        "/api/v1/users/me/password",
        json={"current_password": WRONG, "new_password": NEW},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text

    # Old password still works (nothing changed).
    assert _login(client, ctx).status_code == 200

    # Correct current password → success.
    resp = client.post(
        "/api/v1/users/me/password",
        json={"current_password": PASSWORD, "new_password": NEW},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    # Login now works with the NEW password (and fails with the old one).
    assert _login(client, ctx, password=NEW).status_code == 200
    assert _login(client, ctx, password=PASSWORD).status_code == 401


def test_login_rejects_inactive_user(client):
    db = SessionLocal()
    ctx = _seed(db, is_active=False)
    db.close()

    resp = _login(client, ctx)
    assert resp.status_code == 401, resp.text
    assert "access_token=" not in resp.headers.get("set-cookie", "")
