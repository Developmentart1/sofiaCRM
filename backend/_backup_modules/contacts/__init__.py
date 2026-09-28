"""Contacts module registration. Mounts contact + company routers."""
from fastapi import APIRouter, FastAPI

from core.event_bus import SyncEventBus
from . import routes


def register_module(app: FastAPI, bus: SyncEventBus) -> APIRouter:
    app.include_router(routes.router, prefix="/api/v1")
    return routes.router
