# Runbook: PostgreSQL outage

**Symptoms:** `PostgresDown`; backend pods NotReady; `/health/ready` returns 503 `{"database":"unreachable"}`.
**Expected self-healing behaviour (verified by `scripts/chaos/db-outage.sh`):** backend pods
leave the Service (readiness) but are **not** restarted (liveness doesn't check the DB).
When the DB returns, `pool_pre_ping` reconnects and pods turn Ready without intervention.

## Diagnose
```bash
kubectl -n $NS get statefulset postgres; kubectl -n $NS describe pod postgres-0
kubectl -n $NS logs postgres-0 --tail=100
kubectl -n $NS get pvc                                   # Bound? full?
kubectl -n $NS exec postgres-0 -- df -h /var/lib/postgresql/data
```
| Finding | Mitigation |
|---|---|
| Pod Pending, PVC unbound | storage class or provisioner issue; `kubectl get sc` |
| Disk full | expand the PVC (if the storage class allows) or prune; then VACUUM |
| Data corruption / accidental deletion | restore from backup: [backup-and-restore.md](backup-and-restore.md) |
| Too many connections | find the client (`pg_stat_activity`); scale the backend down; check pool settings |

## Verify
`kubectl -n $NS rollout status deploy/backend-<color>`; smoke tests pass; `pg_up == 1`.
