"""FastAPI dependencies for authenticated requests — simple, no Annotated."""

from dataclasses import dataclass

from fastapi import Cookie, Header
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from core.database import SessionLocal
from core.errors import UnauthorizedError
from core.security import decode_access_token
from core.tenant import reset_org, reset_user_id, set_org, set_user_id


@dataclass(frozen=True)
class CurrentUser:
    id: str
    organization_id: str
    role: str
    email: str
    full_name: str


def _extract_bearer(authorization: str | None = None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Authorization header must be 'Bearer <token>'")
    return parts[1]


def _token_from_headers(headers: Headers) -> str | None:
    auth = headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    cookie = headers.get("cookie")
    if cookie:
        for part in cookie.split(";"):
            key, _, value = part.strip().partition("=")
            if key == "access_token" and value:
                return value
    return None


class OrgContextMiddleware:
    """ASGI middleware that binds the org ContextVar in the event loop.

    `get_current_user` is a sync dependency: FastAPI runs it via a threadpool,
    so a ContextVar set there does not propagate to the (also threadpool-run)
    endpoint. Setting it here, in the event loop, makes it visible to every
    downstream threadpool call, which copies the loop's context.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        token = _token_from_headers(headers)
        org_token = None
        user_token = None
        if token:
            try:
                payload = decode_access_token(token)
                org = payload.get("org")
                if org:
                    org_token = set_org(str(org))
                sub = payload.get("sub")
                if sub:
                    user_token = set_user_id(str(sub))
            except UnauthorizedError:
                pass
        try:
            await self.app(scope, receive, send)
        finally:
            if org_token is not None:
                reset_org(org_token)
            if user_token is not None:
                reset_user_id(user_token)


def get_current_user(
    authorization: str | None = Header(None),
    access_token: str | None = Cookie(None),
) -> CurrentUser:
    token = _extract_bearer(authorization) or access_token
    if not token:
        raise UnauthorizedError("missing credentials (Bearer token or access_token cookie)")
    payload = decode_access_token(token)
    sub = payload.get("sub")
    org = payload.get("org")
    role = payload.get("role")
    if not sub or not org or not role:
        raise UnauthorizedError("token missing required claims")
    set_org(str(org))
    return CurrentUser(
        id=str(sub),
        organization_id=str(org),
        role=str(role),
        email=str(payload.get("email", "")),
        full_name=str(payload.get("name", "")),
    )


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
