# Chaos experiments (game day)

Scripts: `scripts/chaos/` (see its README for the experiment matrix).

## Rules of engagement
1. Only in `devsecops360-dev` or staging, never production without approval.
2. State the hypothesis **before** running. Abort if impact exceeds the blast radius.
3. Watch the Grafana dashboard during the run. Record the JSON output in `docs/evidence/chaos/`.

## Windows-native equivalents (PowerShell + kubectl)
```powershell
$ns = 'devsecops360-dev'
# 1. Pod kill → ReplicaSet self-heals
$color = kubectl -n $ns get svc backend -o jsonpath='{.spec.selector.devsecops360/color}'
$pod = kubectl -n $ns get pod -l "app.kubernetes.io/name=backend,devsecops360/color=$color" -o jsonpath='{.items[0].metadata.name}'
Measure-Command { kubectl -n $ns delete pod $pod --grace-period=0 --force; kubectl -n $ns rollout status deploy/backend-$color }

# 2. DB outage → readiness 503, no restarts, auto-recovery
kubectl -n $ns scale statefulset/postgres --replicas=0
kubectl -n $ns get pods -l app.kubernetes.io/name=backend -w      # READY 0/1, RESTARTS unchanged
kubectl -n $ns scale statefulset/postgres --replicas=1

# 3. Compose
docker compose kill -s SIGKILL backend; docker compose ps          # restarts automatically
```

## Results log template
| Date | Experiment | Hypothesis | Observed | Recovery (s) | Pass? | Follow-up |
|---|---|---|---|---|---|---|
| | kill-pod | replacement Ready ≤ 60 s | | | | |
| | db-outage | NotReady during, Ready after, 0 restarts | | | | |
| | cpu-stress-hpa | scales > 1 replica | | | | |
| | bad release | switch blocked, users unaffected | | | | |
