# Runbook: BackendDown

**Symptoms:** `up{job="backend"} == 0`; the frontend shows "Network error"; `/health/ready` fails.
**Impact:** full outage of the API (SEV1).

## Diagnose
```bash
NS=devsecops360-dev
kubectl -n $NS get deploy,pods -l app.kubernetes.io/name=backend -o wide
kubectl -n $NS describe pod <pod>          # look at Events: OOMKilled? ImagePullBackOff? probe failures?
kubectl -n $NS logs <pod> --previous       # logs of the crashed container
kubectl -n $NS get endpoints backend       # empty = no ready pods behind the Service
```
| Finding | Likely cause | Mitigation |
|---|---|---|
| `CrashLoopBackOff` right after a deploy | bad release or config | `deployment/rollback/rollback.sh` |
| `OOMKilled` | memory limit too low or a leak | raise the limit in the overlay; check memory panels |
| `ImagePullBackOff` | wrong tag or registry auth | fix the tag; `kind load docker-image` locally |
| Readiness failing, liveness OK | DB unreachable | see [database-outage.md](database-outage.md) |
| `CreateContainerConfigError` | missing Secret or ConfigMap key | `kubectl -n $NS get secret backend-secrets`; re-run create-secrets |
| Endpoints empty, pods Running | Service selector points at a colour with 0 ready pods | `rollback.sh` (it scales up the target first) |

**Compose:** `docker compose ps`, `docker compose logs --tail=100 backend`, `docker compose up -d backend`.

## Verify
`SMOKE_BASE_URL=http://localhost:8080 pytest tests/smoke -v` passes, and the `up` metric is back to 1.
