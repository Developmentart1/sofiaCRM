"""CRM-Splash FastAPI application — only registers implemented modules."""

import asyncio
import contextlib
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from core.config import get_settings
from core.database import SessionLocal
from core.errors import CRMError
from core.event_bus import configure_bus, get_bus

_settings = get_settings()
logging.basicConfig(level=_settings.log_level)
log = logging.getLogger("crm_splash")

_DISPATCH_INTERVAL_SECONDS = 2.0


async def _dispatch_loop(interval: float = _DISPATCH_INTERVAL_SECONDS) -> None:
    """Deliver outbox events to subscribers on a short interval (MVP scope)."""
    while True:
        try:
            db = SessionLocal()
            try:
                get_bus().dispatch_pending(db=db)
                db.commit()
            finally:
                db.close()
        except Exception:  # noqa: BLE001 — keep the loop alive
            log.exception("event_bus.dispatch_loop_error")
        await asyncio.sleep(interval)


def create_app() -> FastAPI:
    settings = get_settings()
    bus = configure_bus()

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(_dispatch_loop())
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="CRM-Splash API",
        version="1.0.0",
        description="Multi-tenant CRM with RBAC, automation, and audit.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Bind the org ContextVar in the event loop (see OrgContextMiddleware docs).
    from modules.users.auth_deps import OrgContextMiddleware

    app.add_middleware(OrgContextMiddleware)

    # Security guard: detección + respuesta inicial (ver core/security_guard.py).
    from core.security_guard import SecurityGuardMiddleware

    app.add_middleware(SecurityGuardMiddleware)

    # Register implemented modules (order: dependencies first)
    from modules.organizations import register_module as register_orgs
    from modules.users import register_module as register_users

    register_orgs(app, bus)
    register_users(app, bus)

    from modules.contacts import register_module as register_contacts
    register_contacts(app, bus)

    from modules.pipelines import register_module as register_pipelines
    register_pipelines(app, bus)

    from modules.opportunities import register_module as register_opportunities
    register_opportunities(app, bus)

    from modules.tasks import register_module as register_tasks
    register_tasks(app, bus)

    from modules.activities import register_module as register_activities
    register_activities(app, bus)

    from modules.arm import register_module as register_arm
    register_arm(app, bus)

    from modules.automations import register_module as register_automations
    register_automations(app, bus)

    from modules.documents import register_module as register_documents
    register_documents(app, bus)

    from modules.reports import register_module as register_reports
    register_reports(app, bus)

    # Exception handlers
    @app.exception_handler(CRMError)
    async def _crm_error_handler(_request: Request, exc: CRMError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "validation_error", "message": "validation failed", "details": {"errors": exc.errors()}}},
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(_request: Request, exc: IntegrityError) -> JSONResponse:
        log.warning("integrity error: %r", exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": "integrity_error", "message": "constraint violated"}},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "internal server error"}})

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {"message": "CRM-Splash API", "docs": "/docs"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
