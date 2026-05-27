"""Password hashing, API key generation/hashing, and JWT helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings


API_KEY_PREFIX = "af_"

# bcrypt truncates passwords > 72 bytes; we hash first to avoid that limit
# and to support arbitrary-length passwords safely.
_BCRYPT_PEPPER = b"apiforge:pwd:"


def _prepare_password(password: str) -> bytes:
    pre = _BCRYPT_PEPPER + password.encode("utf-8")
    return hashlib.sha256(pre).digest()


# --- Passwords ---------------------------------------------------------------


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_prepare_password(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare_password(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- API keys ----------------------------------------------------------------


def generate_api_key() -> str:
    """Generate a new API key: prefix + uuid4 (hex, no dashes)."""
    return f"{API_KEY_PREFIX}{uuid.uuid4().hex}"


def hash_api_key(api_key: str) -> str:
    """Deterministic, peppered SHA-256 hash for fast lookups.

    Passwords use bcrypt (slow, salted). API keys must be hashed
    deterministically so we can find them with an indexed lookup, so we
    use HMAC-SHA256 with the application secret as the pepper.
    """
    settings = get_settings()
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        api_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def api_key_prefix_display(api_key: str) -> str:
    """First 10 chars (e.g. "af_a1b2c3d") for display."""
    return api_key[:10]


def secure_compare(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)


# --- JWTs --------------------------------------------------------------------


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> tuple[str, int]:
    """Return `(token, expires_in_seconds)`."""
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
