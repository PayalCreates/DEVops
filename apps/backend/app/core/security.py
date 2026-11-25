"""Password hashing (bcrypt) and JWT creation/verification."""

import os
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

# bcrypt only uses the first 72 bytes; we enforce max length in schemas.
_BCRYPT_ROUNDS = 12

# bcrypt is deliberately CPU-expensive. Allowing more concurrent hashes than CPU
# cores only adds context switching and starves threads that hold DB connections
# (measured with Locust, see docs/testing/performance-report.md).
_HASH_SLOTS = threading.BoundedSemaphore(max(1, os.cpu_count() or 1))


def hash_password(password: str) -> str:
    with _HASH_SLOTS:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(_BCRYPT_ROUNDS)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        with _HASH_SLOTS:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": settings.app_name,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.app_name,
        options={"require": ["exp", "sub", "iat"]},
    )
