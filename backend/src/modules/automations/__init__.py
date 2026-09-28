"""Automations module registration.

Subscribes the engine's ``handle_event`` to every known event type so any
event can trigger automation rules. The engine is tenant-scoped by the event's
``organization_id`` and enforces anti-recursion via ContextVars.
"""
from fastapi import APIRouter, FastAPI

from . import routes
from .engine import all_event_classes, handle_event


def register_module(app: FastAPI, bus=None) -> APIRouter:
    if bus is not None:
        for event_cls in all_event_classes():
            bus.subscribe_event(event_cls, handle_event)
    app.include_router(routes.router, prefix="/api/v1")
    return routes.router
