# Runbook: HighLatencyP95 (> 300 ms)

## Diagnose
1. **p95 latency by route** panel: is one route slow, or are all routes slow?
2. **In-flight requests** rising while CPU is low → waiting on the DB or the pool.
   CPU at the limit (`kubectl top pods`) → CPU-bound (e.g. bcrypt on login/register).
3. DB: `kubectl -n $NS exec -it postgres-0 -- psql -U devsecops -d devsecops360 -c "select state, count(*) from pg_stat_activity group by 1"`
4. Slow queries: enable `pg_stat_statements` (extension is pre-created) and sort by `mean_exec_time`.

## Known bottleneck (found by load testing, fixed)
Auth endpoints held a pooled DB connection during bcrypt (~250 ms CPU). At 100 users the
pool was exhausted, which produced 30 s waits and 500s. Fixed by hashing outside the
connection, a 5 s pool timeout returning 503, and a bcrypt concurrency cap.
Details: `docs/testing/performance-report.md`.

## Mitigate
- Scale out: raise HPA `maxReplicas` or the replica count.
- Raise the container CPU limit if throttled (`container_cpu_cfs_throttled_seconds_total`).
- Roll back if the regression came with a release.
