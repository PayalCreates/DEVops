# Project milestones & status

Legend: ✅ implemented and verified in the build sandbox · 🟡 implemented, validated statically, run it on your machine or in CI · ⬜ future work

| # | Milestone | Status | Verification |
|---|---|---|---|
| 1 | Environment setup & GitHub repository | 🟡 | Repo structure, `.gitignore`/`.gitattributes`, templates. Push to GitHub and enable branch protection yourself. |
| 2 | Architecture, requirements, threat model, plan | ✅ | `docs/architecture`, `docs/adr` (11), `docs/security/threat-model.md` |
| 3 | Application development | ✅ | Backend + frontend running together on PostgreSQL; screenshots |
| 4 | Testing & code quality | ✅ | 60 backend (97.9 %), 20 frontend (79.3 %), 4 E2E; ruff, bandit, eslint, tsc clean |
| 5 | Docker & containerisation | 🟡 | Dockerfiles pass hadolint; Compose config valid; **build/run on your machine** |
| 6 | CI pipelines & security scanning | 🟡 | 5 workflows pass actionlint; pip-audit, npm audit, bandit and Semgrep executed clean; Trivy/gitleaks run in CI |
| 7 | Container registry & CD | 🟡 | `delivery.yml` (GHCR, SBOM, cosign, provenance); runs on push to `main` |
| 8 | Kubernetes deployment | 🟡 | 3 overlays render; 36/36 objects pass strict K8s 1.31 schema; policy check clean; apply on kind |
| 9 | Terraform infrastructure | 🟡 | 17 files parse; module interfaces checked; `terraform validate` in CI; apply locally |
| 10 | Ansible automation | 🟡 | Syntax check + ansible-lint (production profile) pass; run in WSL |
| 11 | Monitoring, logging & alerting | 🟡 | PromQL (34 expressions) parses; metric contract verified on live app; dashboards generated; start with `--profile monitoring` |
| 12 | Blue-green deployment & rollback | ✅ / 🟡 | Switch, no-switch and auto-rollback logic proven by 6 tests against fake kubectl; run on kind |
| 13 | Load & reliability testing | ✅ | Locust baseline + stress; bottleneck found, fixed, re-measured |
| 14 | Backup & disaster recovery | ✅ / 🟡 | pg_dump/restore measured (0.18 s / 0.17 s, counts match); CronJobs/Compose scripts to run on your machine |
| 15 | Failure injection & self-healing | 🟡 | Scripts written (shellcheck clean); run on kind / Compose |
| 16 | Documentation & evidence | ✅ | README, guides, runbooks (9), SRE, security, testing, evidence |
| 17 | Academic report & presentation | ✅ | `docs/report/` (fill in your name; add your own run screenshots) |
| 18 | Production-readiness review & viva prep | ✅ | `docs/report/viva-questions.md` (60), evaluation mapping |

## Your next steps (in order)
1. `git init`, first signed commit, push to GitHub, enable branch protection and private vulnerability reporting.
2. `.\scripts\dev.ps1 up`, then smoke and E2E against Compose. Screenshot `docker compose ps`.
3. Push to GitHub and let CI, Security and Delivery run. Screenshot the run graph and Security tab.
4. `terraform apply`, `deploy-k8s.ps1`, blue-green and rollback, chaos scripts. Save the JSON outputs in `docs/evidence/`.
5. `.\scripts\dev.ps1 up-full`, a Locust run, then screenshot the Grafana dashboard.
6. Replace the `your-github-username` placeholders (CODEOWNERS, overlays, Argo CD apps, Dockerfile labels).

## Future work
⬜ Kyverno admission (signed images only) · ⬜ Argo Rollouts canary with SLO analysis ·
⬜ OpenTelemetry tracing · ⬜ PostgreSQL HA + PITR · ⬜ OIDC/MFA · ⬜ DORA metrics dashboard · ⬜ OWASP ZAP DAST stage
