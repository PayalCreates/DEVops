# Runbook: High error rate / error budget burn

**Symptoms:** `HighErrorRate` (> 5 % 5xx) or `ErrorBudgetFastBurn` / `ErrorBudgetSlowBurn`.

## Diagnose
1. Grafana → **Errors / s by status** and **Requests / s by route**: which route and which status?
2. Loki: `{service="backend", level="ERROR"} | json | line_format "{{.route}} {{.msg}} {{.request_id}}"`
3. Correlate with deploys: `kubectl -n $NS get svc backend -o jsonpath='{.metadata.annotations}'` (shows `switched-at`).
4. Status code meaning in this app:
   | Status | Meaning here |
   |---|---|
   | 500 | unhandled exception (bug); the response body has a `request_id`, so grep Loki for it |
   | 503 | DB unavailable or connection pool exhausted (`database_unavailable` log); see high-latency / database-outage |
   | 429 | login rate limit; not a 5xx and not counted in the SLI |

## Mitigate
- Started after a release → **roll back**: `deployment/rollback/rollback.sh`.
- 503 with `TimeoutError` (pool exhaustion) → scale out: `kubectl -n $NS scale deploy/backend-<color> --replicas=3` (the HPA also reacts to CPU).
- A single route failing → feature-flag or hotfix through the normal pipeline (blue-green).

## Verify
The error ratio panel drops below 0.5 %. The burn-rate alert resolves (its 5 m window clears quickly).
