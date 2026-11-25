"""Post-deployment smoke tests against a RUNNING environment.

Run:  SMOKE_BASE_URL=http://localhost:8080 pytest tests/smoke -v
Skipped automatically when SMOKE_BASE_URL is not set (e.g. in unit-test runs).
Used by: docker compose verification, CD pipeline, blue-green switch validation.
"""

import os
import uuid

import httpx
import pytest

BASE = os.getenv("SMOKE_BASE_URL")
EXPECTED_COLOR = os.getenv("SMOKE_EXPECTED_COLOR")  # optional: assert blue/green
pytestmark = pytest.mark.skipif(not BASE, reason="SMOKE_BASE_URL not set")


@pytest.fixture(scope="module")
def http():
    with httpx.Client(base_url=BASE, timeout=10, follow_redirects=True) as c:
        yield c


def test_frontend_served(http):
    r = http.get("/")
    assert r.status_code == 200 and "<div id=\"root\">" in r.text


def test_backend_ready(http):
    r = http.get("/health/ready")
    assert r.status_code == 200, r.text
    assert r.json()["database"] == "ok"


def test_expected_color(http):
    if not EXPECTED_COLOR:
        pytest.skip("SMOKE_EXPECTED_COLOR not set")
    assert http.get("/api/v1/version").json()["color"] == EXPECTED_COLOR


def test_critical_user_journey(http):
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    r = http.post("/api/v1/auth/register", json={
        "email": email, "password": "Sm0keTest!Pass", "full_name": "Smoke Test"})
    assert r.status_code == 201, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    t = http.post("/api/v1/tasks", json={"title": "smoke task"}, headers=h)
    assert t.status_code == 201
    tid = t.json()["id"]
    assert http.get(f"/api/v1/tasks/{tid}", headers=h).status_code == 200
    assert http.get("/api/v1/analytics/summary", headers=h).status_code == 200
    assert http.delete(f"/api/v1/tasks/{tid}", headers=h).status_code == 204
