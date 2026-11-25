# Evidence

Evidence must be **real output from real runs**. Everything in this folder was produced by
actually executing the system; nothing is mocked up.

## Already captured (during the build of this repository)
| Folder / file | What | How it was produced |
|---|---|---|
| `screenshots/01-login.png` | Login page | Playwright (real Chrome) against the running app (FastAPI + PostgreSQL 16 + built SPA) |
| `screenshots/02-dashboard-team.png` | Manager dashboard, team view, analytics | same |
| `screenshots/03-tasks.png` | Task list with filters, priorities, overdue highlighting, pagination | same |
| `screenshots/04-new-task-modal.png` | Create-task modal | same |
| `screenshots/05-users-rbac.png` | Users page (manager: read-only RBAC view) | same |
| `screenshots/06-mobile-tasks.png` | Responsive layout at 390 px | same |
| `load-tests/baseline-25u*` | Locust 25 users: CSV stats + HTML report | `locust … -u 25 -r 5 -t 2m` |
| `load-tests/stress-100u*` | 100 users **before** the fix | `-u 100 -r 10 -t 90s` |
| `load-tests/stress-100u-after-fix*` | after F1 (hash outside transaction, fail-fast 503) | same profile |
| `load-tests/stress-100u-after-fix2*` | after F1+F2 (bcrypt concurrency cap) | same profile |

Summary of all executed checks: [`../testing/test-results.md`](../testing/test-results.md).

## Capture on your machine (checklist for the report)
| # | Evidence | Command | Save as |
|---|---|---|---|
| 1 | All containers healthy | `docker compose ps` | `compose/ps.png` |
| 2 | RAM usage within budget | `docker stats --no-stream` | `compose/stats.png` |
| 3 | CI, Security, Delivery green | GitHub Actions run graph | `ci/*.png` |
| 4 | Security tab (SARIF results) | GitHub → Security → Code scanning | `security/code-scanning.png` |
| 5 | SBOM artefact + `cosign verify` output | Delivery run → artefacts / logs | `security/sbom.json`, `security/cosign-verify.txt` |
| 6 | Cluster objects | `kubectl -n devsecops360-dev get all,netpol,hpa,pdb,cronjob` | `k8s/objects.txt` |
| 7 | Blue-green switch JSON + UI badge before/after | `blue-green-deploy.ps1` | `bluegreen/deploy.txt`, `bluegreen/*.png` |
| 8 | Rollback JSON (seconds) | `rollback.ps1` | `bluegreen/rollback.txt` |
| 9 | Chaos results | `scripts/chaos/*.sh` | `chaos/*.json` |
| 10 | Restore verification | `kubectl logs job/<restore-verify>` | `dr/restore-verify.txt` |
| 11 | Grafana dashboard under load | screenshot during Locust | `observability/grafana.png` |
| 12 | Alert firing in Alertmanager | stop the backend for 2 min | `observability/alert.png` |
| 13 | Ansible idempotency | 2nd run `changed=0` | `ansible/idempotent.txt` |
| 14 | `terraform apply` summary | | `terraform/apply.txt` |
