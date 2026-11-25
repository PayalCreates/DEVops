# SRE: SLIs, SLOs, error budgets and alerting

## 1. Service level indicators (what we measure)
| SLI | Definition (PromQL source: `observability/prometheus/rules/slo-recording.yml`) |
|---|---|
| **Availability** | `1 − (5xx responses / all responses)`, excluding `/health*` and `/metrics` |
| **Latency** | share of requests completed in < 300 ms (`http_request_duration_seconds_bucket{le="0.3"}`) |
| **Freshness of backups** | age of the newest verified backup (from the restore-verify job output) |

Measured at the backend (server side). Health checks are excluded so probes don't inflate availability.

## 2. Service level objectives (30-day rolling window)
| SLO | Target | Error budget |
|---|---|---|
| Availability | **99.5 %** | 0.5 % of requests ≈ **3 h 36 min** of full outage per 30 days |
| Latency | **95 %** of requests < 300 ms | 5 % of requests may be slower |
| Backup RPO | newest verified backup ≤ **6 h** old (production: 1 h) | — |
| Restore RTO | service restored from backup in ≤ **30 min** | — |

**Why 99.5 % and not 99.99 %?** A single-region, single-database system cannot honestly
promise 4 nines. The SLO is set where users stop being unhappy and where we can afford
the engineering. Each extra "9" costs roughly 10× more.

## 3. Error budget policy
| Budget remaining (30 d) | Action |
|---|---|
| > 50 % | Ship normally. Chaos experiments allowed in staging. |
| 25–50 % | Releases require a passing load test; no risky migrations. |
| < 25 % | Feature freeze: only reliability fixes and security patches ship. |
| Exhausted | Freeze plus a post-incident review; the next sprint prioritises reliability work. |

The `slo:error_budget_remaining:ratio30d` recording rule drives the Grafana stat panel.

## 4. Alerting strategy (symptoms, not causes)
Multi-window, multi-burn-rate alerts (Google SRE Workbook, ch. 5):

| Alert | Condition | Meaning | Severity |
|---|---|---|---|
| `ErrorBudgetFastBurn` | error ratio > 14.4 × 0.5 % over **1 h** AND **5 m** | 2 % of the monthly budget gone in 1 h; budget exhausted in ~2 days | critical (page) |
| `ErrorBudgetSlowBurn` | > 6 × 0.5 % over **6 h** AND **30 m** | steady leak; exhausted in ~5 days | warning (ticket) |
| `HighLatencyP95` | p95 > 300 ms for 10 m | latency SLO at risk | warning |
| `BackendDown` | `up == 0` for 1 m | no scrape target | critical |
| `PostgresDown` | `pg_up == 0` for 1 m | DB unreachable | critical |
| `LoginBruteForceSuspected` | failed + rate-limited logins > 1/s for 5 m | possible attack | warning (security) |

The short window makes the alert **reset quickly** once fixed; the long window prevents
**paging on blips**. Alertmanager inhibits error and latency alerts while `BackendDown`
fires, to avoid alert storms. Every alert carries a `runbook_url`.

## 5. Toil reduction & automation
| Toil | Automated by |
|---|---|
| Deploying | Delivery pipeline + blue-green script |
| Rolling back | `rollback.sh` (one selector patch) or automatic on failed verification |
| Restarting crashed pods | liveness probes and the ReplicaSet controller |
| Taking backups / proving they restore | `db-backup` + `db-restore-verify` CronJobs |
| Scaling for load | HPA (CPU 70 %, memory 80 %) |
| Rotating dependencies | Dependabot |

## 6. Measured results
See `docs/testing/performance-report.md`. On a 2-vCPU sandbox at 25 concurrent users,
p95 was 24 ms with 0 % errors, comfortably inside both SLOs. Kubernetes-level recovery
numbers (pod kill, DB outage) are produced by `scripts/chaos/*` on your cluster. Record
them in `docs/evidence/`.
