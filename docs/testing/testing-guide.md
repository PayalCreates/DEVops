# Testing guide

## Test pyramid

```mermaid
flowchart TB
    e2e["E2E — Playwright (4) · real browser against the running stack"]
    smoke["Smoke — pytest + in-cluster smoke_check.py · post-deploy & blue-green gates"]
    integ["Integration / API — pytest + TestClient + real PostgreSQL (30)"]
    deploy["Deployment logic — real bash scripts vs fake kubectl (6) · manifest policy (6)"]
    unit["Unit — backend (18) · frontend Vitest + Testing Library (20)"]
    e2e --- smoke --- integ --- deploy --- unit
```

| Layer | Location | Tooling | Runs in |
|---|---|---|---|
| Unit (backend) | `tests/unit/` | pytest | CI `backend` job, `pytest` |
| Unit (frontend) | `apps/frontend/src/test/` | Vitest + Testing Library + jsdom | CI `frontend` job, Docker build |
| Integration / API | `tests/integration/` | pytest + FastAPI TestClient + **PostgreSQL 16** (CI service) | CI `backend` job |
| Deployment logic | `tests/deployment/` | pytest + bash + fake kubectl; Kustomize render + policy | CI `backend` job |
| Smoke | `tests/smoke/`, `deployment/scripts/smoke_check.py` | httpx / urllib | CI `e2e` job, blue-green pre/post-switch, CD |
| E2E | `tests/e2e/` | Playwright (Chromium) | CI `e2e` job against Docker Compose |
| Load | `load-testing/` | Locust with SLO gate | on demand / before releases |
| Chaos | `scripts/chaos/` | bash + kubectl | game days, CD (kill-pod) |
| Static | ruff, bandit, eslint, tsc, semgrep, hadolint, shellcheck, actionlint, yamllint, ansible-lint, terraform validate, kubeconform | | CI |

## What the integration tests prove (selected)
- **Auth:** register, login, `/me`; duplicate emails (case-insensitive) → 409; uniform 422 shape.
- **Security:** no role escalation at registration; identical response for unknown user vs wrong password; rate limit → 429; deactivated user's valid token → 401; tampered, expired and `alg=none` JWTs are rejected.
- **RBAC:** user ✗ `/users`; manager reads all but can't change roles; admin promotes but can't demote self.
- **Isolation:** users get 404 on other users' tasks (read, update, delete) and the `all_users` flag is ignored for them.
- **Features:** CRUD lifecycle, completion timestamps, filter/search/sort/paginate, invalid sort column → 422, analytics maths.
- **Platform:** liveness vs readiness (DB outage → 503), security headers, request-id propagation, Prometheus route templates (no ID cardinality), DB pool exhaustion → 503 + `Retry-After`, real Alembic migrations, idempotent seed.

## Commands
```powershell
# Backend (repo root). SQLite by default:
python -m pytest
# Against PostgreSQL (what CI does):
$env:TEST_DATABASE_URL = 'postgresql+psycopg://user:pass@localhost:5432/ds360_test'; python -m pytest --cov=apps/backend/app
# Frontend:
cd apps/frontend; npm test; npm run test:coverage
# Smoke (stack running on :8080):
$env:SMOKE_BASE_URL='http://localhost:8080'; python -m pytest tests/smoke -v
# E2E:
cd tests/e2e; npm ci; npx playwright install chromium; $env:E2E_BASE_URL='http://localhost:8080'; npx playwright test
# Load (SLO-gated):
locust -f load-testing/locustfile.py --host http://localhost:8080 --headless -u 25 -r 5 -t 3m
```

## Quality gates (CI fails if…)
- any test fails; backend coverage < **85 %**;
- ruff, bandit (medium+), eslint or tsc report errors;
- the migration upgrade → downgrade → upgrade round-trip fails;
- smoke or Playwright fail against the freshly built Compose stack;
- a security or policy gate fails (see the security guide).

Actual results from the build of this repository: [test-results.md](test-results.md).
