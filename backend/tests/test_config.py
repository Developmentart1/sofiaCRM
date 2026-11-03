"""Security configuration tests ? production must reject default secrets."""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import pytest

from core.config import DEFAULT_JWT_SECRET, DEFAULT_SECRET_KEY, Settings


def test_production_rejects_default_jwt_secret():
    """Settings must refuse the dev JWT secret outside dev/test."""
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(
            env="production",
            jwt_secret=DEFAULT_JWT_SECRET,
            secret_key="strong-random-secret-not-default",
        )


def test_production_rejects_default_secret_key():
    """Settings must refuse the dev SECRET_KEY outside dev/test."""
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            env="production",
            jwt_secret="strong-random-jwt-not-default",
            secret_key=DEFAULT_SECRET_KEY,
        )


def test_production_accepts_strong_secrets():
    """Strong secrets pass the production validator."""
    s = Settings(
        env="production",
        jwt_secret="strong-random-jwt-not-default",
        secret_key="strong-random-secret-not-default",
    )
    assert s.env == "production"


def test_dev_environment_allows_default_secrets():
    """Development keeps working with the default secrets."""
    s = Settings(
        env="development",
        jwt_secret=DEFAULT_JWT_SECRET,
        secret_key=DEFAULT_SECRET_KEY,
    )
    assert s.jwt_secret == DEFAULT_JWT_SECRET
