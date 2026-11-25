# Failure injection & self-healing experiments

Each experiment states a **hypothesis**, injects one failure, measures recovery and
prints a JSON result line you can paste into `docs/evidence/`. Run them against the
dev namespace only.

| Script | Platform | Failure injected | Self-healing mechanism | Pass criteria |
|---|---|---|---|---|
| `kill-pod.sh` | Kubernetes | Force-delete an active backend pod | Deployment/ReplicaSet controller | Replacement Ready ≤ 60 s |
| `db-outage.sh` | Kubernetes | Scale PostgreSQL to 0 | Readiness probe removes pods from Service; `pool_pre_ping` reconnects | NotReady during outage, Ready again after, **0 restarts** |
| `cpu-stress-hpa.sh` | Kubernetes | In-cluster load spike | HorizontalPodAutoscaler | Replicas > 1 during spike |
| `compose-chaos.sh kill-backend` | Compose | SIGKILL the backend | `restart: unless-stopped` + healthcheck | `/health/ready` 200 again ≤ 90 s |
| `compose-chaos.sh db-outage` | Compose | Stop the db container | Readiness returns 503; pool reconnects | 503 during, 200 after, no backend restart |
| `deployment/scripts/blue-green-deploy.sh` with a broken image | Kubernetes | Bad release | Pre-switch smoke test blocks the switch / post-switch auto-rollback | Users never routed to the broken colour |

```bash
NAMESPACE=devsecops360-dev ./scripts/chaos/kill-pod.sh
NAMESPACE=devsecops360-dev ./scripts/chaos/db-outage.sh
DURATION=120 NAMESPACE=devsecops360-dev ./scripts/chaos/cpu-stress-hpa.sh
./scripts/chaos/compose-chaos.sh kill-backend
```

Windows: run these from WSL2 Ubuntu (they're bash), or use the equivalent
`kubectl delete pod` / `kubectl scale` commands listed in `docs/runbooks/chaos-experiments.md`.

**Bad-release drill** (proves the blue-green safety net):

```bash
# An image whose readiness never passes: the switch must NOT happen.
docker tag devsecops360-backend:local devsecops360-backend:broken
kind load docker-image --name devsecops360 devsecops360-backend:broken
kubectl -n devsecops360-dev set env deploy/backend-green DATABASE_URL=postgresql+psycopg://x:y@nowhere:5432/z
./deployment/scripts/blue-green-deploy.sh devsecops360-backend:broken   # expect: "did not become ready — traffic still on blue"
kubectl -n devsecops360-dev set env deploy/backend-green DATABASE_URL-   # undo
```
