"""Pytest bootstrap: point the app at a TEMPORARY SQLite DB and migrate it once.

The project's real ``crm_splash.db`` is never touched. All tests share one
migrated temp DB; helpers use unique IDs per test to avoid collisions.
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SRC = BACKEND / "src"
sys.path.insert(0, str(SRC))

_TMPDIR = tempfile.mkdtemp(prefix="crm_splash_test_")
_TEST_DB = os.path.join(_TMPDIR, "test.db")
_STORAGE = os.path.join(_TMPDIR, "storage")

# Set BEFORE importing any app module so the engine binds to the temp DB.
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["ENV"] = "test"
os.environ["STORAGE_ROOT"] = _STORAGE

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrate_db():
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{_TEST_DB}")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from src.main import app

    with TestClient(app) as c:
        yield c
