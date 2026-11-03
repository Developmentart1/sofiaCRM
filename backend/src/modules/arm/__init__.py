"""ARM module registration."""

from fastapi import APIRouter, FastAPI

from . import router


def register_module(app: FastAPI, bus=None) -> APIRouter:
    app.include_router(router.router, prefix="/api/v1")
    return router.router
