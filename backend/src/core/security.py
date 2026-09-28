"""Security primitives: password hashing, JWT, signed URL helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings
from .errors import UnauthorizedError

_settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_url_signer = URLSafeTimedSerializer(_settings.secret_key, salt="crm-storage-url")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash. Bcrypt truncates at 72 bytes; we mirror that."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def create_access_token(
    *,
    subject: str,
    organization_id: str,
    role: str,
    extra: dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """Create a signed JWT carrying subject, org and role."""
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else _settings.jwt_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "org": organization_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises UnauthorizedError on any failure."""
    try:
        return jwt.decode(token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm])
    except JWTError as exc:
        raise UnauthorizedError("invalid or expired token", details={"reason": str(exc)}) from exc


def sign_storage_url(path: str) -> str:
    """Create a tamper-proof URL for a stored object. Expires per config."""
    return _url_signer.dumps(path)


def verify_storage_url(token: str, max_age: int | None = None) -> str:
    """Return the path encoded in a signed token, or raise UnauthorizedError."""
    try:
        return _url_signer.loads(
            token,
            max_age=max_age if max_age is not None else _settings.storage_url_max_age_seconds,
        )
    except SignatureExpired as exc:
        raise UnauthorizedError("signed url expired") from exc
    except BadSignature as exc:
        raise UnauthorizedError("invalid signed url") from exc
