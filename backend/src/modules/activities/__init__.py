"""Activities module registration.

Subscribes the ``OpportunityStageChanged`` handler on the event bus so a
``stage_change`` activity is recorded whenever an opportunity moves stages.
Delivery is synchronous (see ``core.event_bus.publish``), so the activity is
written in the same request/transaction as the stage transition.
"""
from fastapi import APIRouter, FastAPI

from core.event_bus import OpportunityStageChanged
from . import routes
from .service import record_stage_change


def register_module(app: FastAPI, bus=None) -> APIRouter:
    if bus is not None:
        bus.subscribe_event(OpportunityStageChanged, record_stage_change)
    app.include_router(routes.router, prefix="/api/v1")
    return routes.router
