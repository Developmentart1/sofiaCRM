"""Documents module registration — dual prefix (see ``routes.py``).

CRUD routes live under ``/api/v1/documents``; upload/download are additionally
served under ``/api/documents`` because the frontend ``documents.ts`` fetches
those directly (no Next.js rewrite, no ``/v1``).
"""
from fastapi import APIRouter, FastAPI

from . import routes


def register_module(app: FastAPI, bus=None) -> APIRouter:
    app.include_router(routes.v1_router, prefix="/api/v1")
    app.include_router(routes.direct_router, prefix="/api")
    return routes.v1_router
