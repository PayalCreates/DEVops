# 120-mark evaluation mapping

Typical capstone rubric categories mapped to concrete, demonstrable evidence in this
repository. Adjust the weights to your university's official rubric. The evidence
column tells the examiner exactly where to look.

| # | Criterion | Marks | Evidence in repo | Live demo proof |
|---|---|---|---|---|
| 1 | Problem definition, requirements, architecture | 10 | `docs/architecture/architecture.md` (context, app, pipeline, K8s, environments diagrams), `docs/adr/` (11 ADRs) | Walk the architecture diagram |
| 2 | Application implementation (full-stack, auth, RBAC) | 12 | `apps/backend` (FastAPI, JWT, RBAC, analytics, OpenAPI), `apps/frontend` (React/TS, responsive), screenshots `docs/evidence/screenshots/` | Register → tasks → dashboard; admin vs user views |
| 3 | Version control & collaboration | 6 | Branching strategy (README), PR template, CODEOWNERS, Conventional Commits, branch protection, Dependabot | Show a PR with green checks |
| 4 | Testing & code quality | 12 | 18 unit + 30 integration (PostgreSQL) + 12 deployment-logic + 20 frontend + 4 Playwright E2E + smoke; coverage 97.9 % backend / 79.3 % frontend; ruff, bandit, eslint, tsc; `docs/testing/test-results.md` | `pytest`, `npm test`, Playwright report |
| 5 | Containerisation | 8 | Multi-stage Dockerfiles (non-root, healthchecks, OCI labels), Compose with profiles, internal network, read-only FS, limits | `docker compose ps` (healthy), `docker stats` |
| 6 | CI/CD pipelines | 12 | 5 workflows: `ci.yml`, `security.yml`, `codeql.yml`, `delivery.yml`, `iac.yml` (+ Dependabot) | Actions run graph |
| 7 | DevSecOps & supply chain | 12 | gitleaks, Semgrep (+ custom rules), CodeQL, Bandit, pip-audit, npm audit, Trivy fs/config/image gate, SBOM SPDX+CDX, cosign keyless signing + attestation, SLSA provenance; `docs/security/threat-model.md` (STRIDE) | Security tab; `cosign verify` |
| 8 | Kubernetes | 12 | Kustomize base + 3 overlays; Deployments, StatefulSet + PVC, Services, Ingress, ConfigMap, Secret refs, probes, HPA, PDB, RBAC, NetworkPolicies, PSA restricted, LimitRange/Quota, CronJobs, Job; policy-as-code check | `kubectl get all,netpol,hpa,pdb` |
| 9 | Infrastructure as Code & config management | 8 | Terraform: 3 modules, 3 environments, remote-state examples; Ansible: 5 roles, 5 playbooks, Vault, idempotent, ansible-lint `production` profile | `terraform apply` from scratch; Ansible 2nd run `changed=0` |
| 10 | Deployment strategy (blue-green + rollback) | 10 | `kubernetes/blue-green/`, `deployment/scripts/blue-green-deploy.*`, `deployment/rollback/*`, 6 automated tests of the switch/rollback logic, `docs/deployment/blue-green.md` | Live switch: UI badge blue → green; rollback in seconds |
| 11 | Observability & SRE | 10 | Prometheus RED metrics, SLO recording rules, multi-window burn-rate alerts, Alertmanager routing/inhibition, Grafana dashboard-as-code, Loki + Alloy, JSON logs with request-id; `docs/sre/slos.md`; 9 runbooks | Grafana during load test; alert firing |
| 12 | Performance, reliability, DR | 8 | Locust with SLO gate; bottleneck found and fixed (39.6 % → 0.67 % errors); backup/restore + automated restore verification; RPO/RTO; chaos scripts | Locust run; DR drill; kill-pod |
| | **Total** | **120** | | |

## Distinguishing "elite" signals examiners look for
- **Honest measurement:** real before/after numbers, plus a list of what was *not* verified and why (`test-results.md` §3).
- **Failure handling designed in:** readiness vs liveness semantics, fail-fast 503, auto-rollback, restore *verification* (not just backups).
- **Security as code:** custom Semgrep rules encoding the project's own decisions; policy-as-code for manifests; threat model mapped to tests.
- **Reproducibility:** one command per level (`dev.ps1 up`, `terraform apply`, `deploy-k8s`); everything pinned.
- **Trade-offs documented:** ADRs explain why kind not Minikube, Traefik not ingress-nginx, sessionStorage vs cookies, blue-green vs canary.
