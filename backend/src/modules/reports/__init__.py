"""Reports module registration."""
from fastapi import APIRouter, FastAPI

from . import routes


def register_module(app: FastAPI, bus=None) -> APIRouter:
    app.include_router(routes.router, prefix="/api/v1")
    return routes.router
