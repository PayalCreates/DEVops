"""Unit tests: input validation, settings safety rails, rate limiter."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.ratelimit import SlidingWindowLimiter
from app.schemas import TaskCreate, UserCreate


@pytest.mark.parametrize("pw", ["short1A", "alllowercase1", "ALLUPPER123", "NoDigitsHere"])
def test_weak_passwords_rejected(pw):
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", full_name="Al", password=pw)


def test_password_over_72_bytes_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", full_name="Al", password="Aa1" + "x" * 80)


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", full_name="Al", password="GoodPass1")


def test_task_title_is_stripped_and_non_blank():
    assert TaskCreate(title="  Ship it  ").title == "Ship it"
    with pytest.raises(ValidationError):
        TaskCreate(title="    ")


def test_production_rejects_default_secret():
    s = Settings(environment="production", database_url="postgresql://x/y",
                 jwt_secret_key="dev-only-insecure-secret-change-me-0123456789")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        s.validate_production_safety()


def test_production_rejects_sqlite():
    s = Settings(environment="production", jwt_secret_key="k" * 40,
                 database_url="sqlite:///x.db")
    with pytest.raises(RuntimeError, match="SQLite"):
        s.validate_production_safety()


def test_invalid_environment_rejected():
    with pytest.raises(ValidationError):
        Settings(environment="prod")


def test_cors_origins_parsed():
    s = Settings(cors_origins="http://a.com, http://b.com ,")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_rate_limiter_blocks_after_limit():
    lim = SlidingWindowLimiter(limit=3, window_seconds=60)
    assert [lim.allow("k") for _ in range(4)] == [True, True, True, False]
    assert lim.allow("other")
    lim.reset()
    assert lim.allow("k")
