"""Shared pytest fixtures.

The backend reads settings at import time, so the environment is configured
here *before* any `app` module is imported.

- Default: a throwaway SQLite file (fast, zero setup).
- CI / integration: set TEST_DATABASE_URL to a real PostgreSQL database.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND))

_tmp = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", f"sqlite:///{_tmp}")
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256-0123"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["LOGIN_RATE_LIMIT_PER_MINUTE"] = "1000"


@pytest.fixture(scope="session")
def migrated_db():
    """Apply the real Alembic migrations once per test session."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(cfg, "head")
    yield cfg
    command.downgrade(cfg, "base")


@pytest.fixture()
def db_session(migrated_db):
    from sqlalchemy import delete

    from app.db.session import SessionLocal
    from app.models import Task, User

    session = SessionLocal()
    yield session
    session.rollback()
    session.execute(delete(Task))
    session.execute(delete(User))
    session.commit()
    session.close()


@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient

    from app.api.routes.auth import login_limiter
    from app.main import app

    login_limiter.reset()
    with TestClient(app) as c:
        yield c


def _register(client, email: str, password: str = "Str0ngPassw0rd", name: str = "Test User"):  # noqa: S107 - test fixture
    r = client.post("/api/v1/auth/register",
                    json={"email": email, "password": password, "full_name": name})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def register(client):
    return lambda email, **kw: _register(client, email, **kw)


@pytest.fixture()
def auth_headers(register):
    def make(email: str = "user@example.com") -> dict[str, str]:
        token = register(email)["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return make


@pytest.fixture()
def make_admin(db_session, client):
    """Create a user and promote them directly in the DB (no API path to self-promote)."""
    from sqlalchemy import select

    from app.models import Role, User

    def make(email: str = "admin@example.com", role: Role = Role.ADMIN) -> dict[str, str]:
        token = _register(client, email)["access_token"]
        user = db_session.scalar(select(User).where(User.email == email))
        user.role = role
        db_session.commit()
        return {"Authorization": f"Bearer {token}"}
    return make
