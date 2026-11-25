#!/usr/bin/env python3
"""In-cluster smoke check (stdlib only, runs inside the backend image).

    python smoke_check.py http://backend-preview:8000 green

Exits non-zero on the first failure. Used by blue-green-deploy before AND after
the traffic switch. Prints one JSON line per check (easy to grep / ship to Loki).
"""

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = sys.argv[1].rstrip("/")
EXPECTED_COLOR = sys.argv[2] if len(sys.argv) > 2 else None


def call(method, path, body=None, token=None, expect=200):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 - fixed in-cluster URL
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    ms = round((time.perf_counter() - start) * 1000, 1)
    ok = status == expect
    print(json.dumps({"check": f"{method} {path}", "status": status, "ok": ok, "ms": ms}))
    if not ok:
        print(raw[:500].decode(errors="replace"), file=sys.stderr)
        sys.exit(1)
    return json.loads(raw) if raw else None


def main() -> None:
    ready = call("GET", "/health/ready")
    assert ready["database"] == "ok", ready
    version = call("GET", "/api/v1/version")
    if EXPECTED_COLOR and version["color"] != EXPECTED_COLOR:
        print(json.dumps({"check": "color", "ok": False, "expected": EXPECTED_COLOR,
                          "got": version["color"]}))
        sys.exit(1)

    email = f"smoke-{uuid.uuid4().hex[:10]}@example.com"
    auth = call("POST", "/api/v1/auth/register",
                {"email": email, "password": "Sm0ke-Check-Pass", "full_name": "Smoke Check"},
                expect=201)
    token = auth["access_token"]
    task = call("POST", "/api/v1/tasks", {"title": "smoke", "priority": "low"}, token, 201)
    call("GET", f"/api/v1/tasks/{task['id']}", token=token)
    call("PATCH", f"/api/v1/tasks/{task['id']}", {"status": "done"}, token)
    call("GET", "/api/v1/analytics/summary", token=token)
    call("DELETE", f"/api/v1/tasks/{task['id']}", token=token, expect=204)
    call("GET", "/api/v1/tasks", token=None, expect=401)  # auth still enforced
    print(json.dumps({"smoke": "passed", "base": BASE, "color": version["color"],
                      "version": version["version"]}))


if __name__ == "__main__":
    main()
