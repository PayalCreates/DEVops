"""Integration tests: health probes, metrics, security headers, migrations, seed."""

import os

from sqlalchemy import inspect, select


def test_liveness_and_readiness(client):
    live = client.get("/health/live")
    assert live.status_code == 200 and live.json()["status"] == "ok"
    ready = client.get("/health/ready")
    assert ready.status_code == 200 and ready.json()["database"] == "ok"


def test_readiness_reports_db_outage(client, monkeypatch):
    from app.db import session as session_mod

    class Broken:
        def execute(self, *_a, **_k):
            raise ConnectionError("db down")

        def close(self):
            pass

    from app.main import app
    app.dependency_overrides[session_mod.get_db] = lambda: Broken()
    try:
        r = client.get("/health/ready")
        assert r.status_code == 503 and r.json()["database"] == "unreachable"
    finally:
        app.dependency_overrides.clear()


def test_version_endpoint_exposes_color(client):
    j = client.get("/api/v1/version").json()
    assert j["color"] in {"blue", "green"} and j["version"]


def test_security_headers_present(client):
    r = client.get("/health/live")
    for h in ("X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy",
              "Strict-Transport-Security", "X-Request-ID"):
        assert h in r.headers
    assert "server" not in {k.lower() for k in r.headers} or r.headers.get("server") != "uvicorn"


def test_request_id_is_propagated(client):
    r = client.get("/health/live", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"


def test_metrics_endpoint_records_requests(client, auth_headers):
    client.get("/api/v1/tasks", headers=auth_headers())
    text = client.get("/metrics").text
    assert "http_requests_total" in text
    assert 'route="/api/v1/tasks"' in text
    assert "http_request_duration_seconds_bucket" in text


def test_metrics_use_route_templates_not_ids(client, auth_headers):
    h = auth_headers()
    tid = client.post("/api/v1/tasks", json={"title": "x"}, headers=h).json()["id"]
    client.get(f"/api/v1/tasks/{tid}", headers=h)
    assert 'route="/api/v1/tasks/{task_id}"' in client.get("/metrics").text


def test_unknown_route_404_low_cardinality(client):
    assert client.get("/no/such/path/123").status_code == 404
    assert 'route="unmatched"' in client.get("/metrics").text


def test_migrations_created_expected_schema(db_session):
    insp = inspect(db_session.get_bind())
    assert {"users", "tasks", "alembic_version"} <= set(insp.get_table_names())
    cols = {c["name"] for c in insp.get_columns("tasks")}
    assert {"title", "status", "priority", "due_date", "owner_id", "completed_at"} <= cols


def test_seed_is_idempotent(db_session, monkeypatch):
    from app.core.config import get_settings
    from app.models import Role, Task, User
    from app.seed import seed

    monkeypatch.setenv("ADMIN_EMAIL", "root@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "RootPass123")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "DemoPass123")
    get_settings.cache_clear()
    try:
        seed(sample=True)
        seed(sample=True)
    finally:
        get_settings.cache_clear()
        for k in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "DEMO_USER_PASSWORD"):
            os.environ.pop(k, None)
    db_session.expire_all()
    admins = db_session.scalars(select(User).where(User.role == Role.ADMIN)).all()
    assert [a.email for a in admins] == ["root@example.com"]
    assert len(db_session.scalars(select(User)).all()) == 4
    assert len(db_session.scalars(select(Task)).all()) == 11


def test_db_pool_exhaustion_returns_503_not_500(client, auth_headers):
    """Regression test for the Locust stress finding: overload must fail fast with 503."""
    from sqlalchemy.exc import TimeoutError as PoolTimeoutError

    from app.db import session as session_mod
    from app.main import app

    h = auth_headers()

    class Exhausted:
        def __getattr__(self, _name):
            def boom(*_a, **_k):
                raise PoolTimeoutError("QueuePool limit reached")
            return boom

    app.dependency_overrides[session_mod.get_db] = lambda: Exhausted()
    try:
        r = client.get("/api/v1/tasks", headers=h)
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "2"
