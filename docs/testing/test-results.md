# Test & validation results (recorded during the build of this repository)

**Date:** 2026-11-25 · **Environment:** Linux sandbox (2 vCPU), Python 3.13, Node 22,
PostgreSQL 16.15, Google Chrome (Playwright `channel: chrome`).

> These are the results of commands that were **actually executed**. Anything that could not
> be executed in that environment is listed in §3 with the reason and the command to run it
> yourself. Re-run everything on your machine and save the output in `docs/evidence/`.

## 1. Executed and passing

| Area | Command | Result |
|---|---|---|
| Backend unit tests | `pytest tests/unit` | **18 passed** |
| Backend integration/API tests (SQLite) | `pytest tests/integration` | **30 passed** |
| Backend integration/API tests (**PostgreSQL 16**) | `TEST_DATABASE_URL=postgresql+psycopg://… pytest` | **60 passed, 4 skipped** (smoke tests skip without a URL) |
| Deployment logic (bash scripts vs fake kubectl) | `pytest tests/deployment` | **12 passed** (6 blue-green/rollback flows + 6 manifest/policy) |
| Backend coverage | `pytest --cov=apps/backend/app --cov-fail-under=85` | **97.9 %** (660 statements, 14 missed) |
| Alembic migration round-trip on PostgreSQL | `alembic upgrade head && alembic downgrade base && alembic upgrade head` | ✅ |
| Frontend unit tests | `npm test` | **20 passed** |
| Frontend coverage | `npm run test:coverage` | **79.3 %** statements, 72.0 % branches |
| Frontend lint / types / build | `npm run lint && npm run typecheck && npm run build` | 0 problems · 0 errors · built (JS 87.7 KB gzip) |
| Smoke tests vs running stack | `SMOKE_BASE_URL=… pytest tests/smoke` | **3 passed**, 1 skipped (colour assertion needs `SMOKE_EXPECTED_COLOR`) |
| In-cluster smoke script (run locally) | `python deployment/scripts/smoke_check.py http://localhost:8000 blue` | `{"smoke": "passed", …}` |
| **E2E (Playwright, real Chrome)** | `npx playwright test` | **4 passed**: full journey (register → create → complete → dashboard 100 % → sign out), weak-password rejection, auth redirect, security headers |
| Load: baseline 25 users | Locust | 2,405 req, **0 % errors, p95 24 ms** |
| Load: stress 100 users (after fixes) | Locust | 4,454 req, 0.67 % errors, p95 170 ms (before fixes: 39.6 % errors, p95 59 s) — see performance report |
| Backup + restore (pg_dump/pg_restore, PostgreSQL 16) | dump → `pg_restore --list` → restore into scratch DB → count rows | backup **0.18 s**, restore **0.17 s**, 56 KB; users 236 = 236, tasks 1,471 = 1,471, Alembic `0001` |
| DB init SQL | `psql -f database/init/01-extensions.sql` | ✅ (`statement_timeout` = 30s applied) |
| Python lint | `ruff check` | All checks passed |
| Python SAST | `bandit -r app -ll` | **No issues identified** |
| Custom Semgrep rules | `semgrep --config security/semgrep-rules.yml` | 0 findings in 41 files; **all 5 rules proven to fire** on a deliberately vulnerable sample |
| Python dependency CVEs | `pip-audit -r apps/backend/requirements.txt` | **No known vulnerabilities found** |
| npm production dependency CVEs | `npm audit --omit=dev` | **found 0 vulnerabilities** |
| Kubernetes manifests: render | `scripts/validate/render_kustomize.py` (all 3 overlays) | 38 objects each |
| Kubernetes manifests: **schema** | `kubernetes-validate -k 1.31.0 --strict` | **36/36 core objects pass** per overlay (2 Traefik CRDs skipped: no schema) |
| Kubernetes policy-as-code | `scripts/validate/k8s_policy_check.py` | 0 violations (the check **caught** `:latest` in production, which was then fixed) |
| Docker Compose | `docker compose --profile monitoring --profile loadtest config -q` | valid (10 services) |
| Dockerfiles | `hadolint` | no warnings |
| GitHub Actions | `actionlint` (with shellcheck) | 5 workflows clean |
| Shell scripts | `shellcheck -S warning` + `bash -n` | 17 scripts, 0 warnings |
| YAML | `yamllint -c .yamllint.yml .` | 0 errors |
| Ansible | `ansible-playbook --syntax-check` (5 playbooks) + `ansible-lint` | syntax OK · **Passed, profile `production`** |
| Terraform | HCL2 parse of 17 files + module-interface check (`scripts/validate/terraform_static_check.py`) | 0 errors |
| PromQL | parse of 18 rule expressions + 16 dashboard queries (`promql-parser`); all referenced recording rules exist; all runbook links resolve | 0 errors |
| Metrics contract | scrape live `/metrics` | every metric used by rules/dashboards is exported (incl. `le="0.3"` bucket) |
| Screenshots | Playwright against the running app | `docs/evidence/screenshots/01–06` |

## 2. Defects found by this validation and fixed
| Found by | Defect | Fix |
|---|---|---|
| Integration test | Prometheus `route` label lost router prefix (`/tasks` instead of `/api/v1/tasks`) | route template rebuilt from path + path params |
| Locust stress test | DB pool exhaustion → 30 s hangs + 500s at 100 users | hash outside transaction, `pool_timeout=5` → 503, bcrypt concurrency cap (+ regression test) |
| Playwright | strict-mode locator ambiguity (two "Priority" selects) | scoped selectors to the task form |
| Screenshot run | demo emails on `.local` rejected by email validator (reserved TLD) | demo domain `devsecops360.dev` |
| Policy check | production overlay used `:latest` | immutable `1.0.0` tag |
| hadolint / actionlint / shellcheck / ansible-lint / yamllint | unpinned pip, shell-form HEALTHCHECK, missing job `needs`, unquoted vars, unprefixed role vars, YAML quoting | all fixed before packaging |

## 3. Not executable in the build sandbox (run these yourself)
| What | Why not | How to validate |
|---|---|---|
| `docker build` / `docker compose up` | registry-1.docker.io blocked by the sandbox network policy (base images can't be pulled) | `.\scripts\dev.ps1 up`, then `docker compose ps` (all healthy) |
| Trivy / gitleaks / image SBOM / cosign | same (container images) | `.\scripts\security-scan.ps1`; CI `security.yml` + `delivery.yml` |
| kind cluster, `kubectl apply`, blue-green on a real cluster, chaos scripts | no Kubernetes available | `terraform apply` → `deploy-k8s.ps1` → `blue-green-deploy.ps1` → `scripts/chaos/*`; CI `delivery.yml` job `deploy-verify` |
| `terraform validate` / `tflint` / `kustomize build` / `kubeconform` / `promtool` | binaries not downloadable in the sandbox | CI `iac.yml` runs all of them |
| Ansible check-mode run | sandbox Python lacks `python3-apt` | `ansible-playbook playbooks/provision-workstation.yml --check` in WSL Ubuntu |
| PowerShell scripts | no `pwsh` in sandbox | run on Windows; logic mirrors the tested bash scripts |
