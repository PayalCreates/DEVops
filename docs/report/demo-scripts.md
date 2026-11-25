# Live demo scripts

## Before the session (T−15 min)
```powershell
Set-Location C:\dev\devsecops360
.\scripts\dev.ps1 up-full                 # Compose + monitoring (or the kind path for the K8s demo)
docker compose ps                         # everything healthy
# Optional K8s demo: cluster already created with terraform, app deployed with deploy-k8s.ps1,
# and a second image built and loaded:
docker build -f docker/backend.Dockerfile -t devsecops360-backend:v1.1.0 --build-arg APP_VERSION=1.1.0 apps/backend
kind load docker-image --name devsecops360 devsecops360-backend:v1.1.0
```
Open tabs: the app (:8080 or :8088), Grafana dashboard, the GitHub Actions run, the GitHub Security tab.
Close everything else (RAM).

---

## 5-minute demo (essentials)
| Time | Say | Do |
|---|---|---|
| 0:00 | "This is the app; the platform around it is the real project." | Log in as `manager@devsecops360.dev`, show the dashboard and team toggle, create a task. |
| 0:45 | "Every change goes through these gates." | GitHub → Actions: show CI, Security and Delivery runs (green), Trivy gate, SBOM artefact, cosign verify step. |
| 1:45 | "Zero-downtime release with automatic safety nets." | K8s: `.\deployment\scripts\blue-green-deploy.ps1 -Image devsecops360-backend:v1.1.0`. Narrate migrate → idle rollout → preview smoke → switch → verify. Refresh the UI: badge **blue → green**. |
| 3:00 | "Rollback is one selector patch." | `.\deployment\rollback\rollback.ps1`, badge back to blue, and point at the `seconds` field in the output. |
| 3:45 | "We measure reliability against objectives." | Grafana: availability, p95, error budget, serving colour panel. |
| 4:30 | "And it heals itself." | `kubectl -n devsecops360-dev delete pod <backend-pod>`, then `kubectl get pods -w` (replacement Ready). Close. |

*(Compose-only fallback for 1:45–3:00: `./scripts/chaos/compose-chaos.sh kill-backend`, which shows auto-restart; then show the blue-green CI job log.)*

---

## 10-minute demo (full story)
1. **App and security (1.5 min):** register a user with a weak password (rejected client-side), then a strong one. Try to open `/users` as a normal user (redirected). Log in as admin and change a role. Show the response headers in DevTools (CSP, X-Frame-Options).
2. **API and observability hooks (1 min):** `/docs` (OpenAPI). `curl -i http://localhost:8080/health/ready`. `curl http://localhost:8000/metrics | Select-String http_requests_total` (inside Compose: Prometheus targets page).
3. **Pipeline (1.5 min):** PR checks, Security tab SARIF results, delivery run: scan, SBOM, sign, then the deploy-verify job (blue-green + rollback drill on kind in CI).
4. **Load test and SLOs (2 min):** `locust ... -u 50 -r 10 -t 1m --headless` while Grafana shows RPS, p95 and in-flight. Explain the bottleneck story and the before/after table.
5. **Blue-green and rollback (2 min):** as in the 5-minute demo, plus `.\deployment\scripts\status.sh`-style output (`kubectl get svc backend -o jsonpath='{.spec.selector}'`).
6. **Failure and recovery (1.5 min):**
   - DB outage: `kubectl -n devsecops360-dev scale statefulset/postgres --replicas=0`. Backend pods go NotReady with **no restarts**, and the UI shows a clean error. Scale back to 1; pods recover by themselves.
   - DR: `kubectl -n devsecops360-dev create job --from=cronjob/db-restore-verify demo-verify`, then `kubectl logs job/demo-verify` → `restore_verify_ok` with timings.
7. **Wrap-up (0.5 min):** "Everything you saw is code in the repo, reproducible with `terraform apply` and one deploy script."

## If something breaks during the demo
Stay calm and turn it into an SRE moment: open the runbook (`docs/runbooks/`), check
`kubectl get events` or `docker compose logs`, and explain your diagnosis. Have the screenshots in
`docs/evidence/` ready as a fallback.
