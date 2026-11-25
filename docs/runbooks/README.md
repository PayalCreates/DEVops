# Runbooks

Every alert links here. Each runbook gives: **symptoms → impact → diagnose → mitigate → verify → follow-up**.
Mitigate first (restore service), investigate second.

| Runbook | Triggered by |
|---|---|
| [incident-response.md](incident-response.md) | Any SEV1/SEV2 — roles, comms, timeline, postmortem |
| [service-down.md](service-down.md) | `BackendDown` |
| [high-error-rate.md](high-error-rate.md) | `HighErrorRate`, `ErrorBudgetFastBurn`, `ErrorBudgetSlowBurn` |
| [high-latency.md](high-latency.md) | `HighLatencyP95` |
| [database-outage.md](database-outage.md) | `PostgresDown`, `PostgresTooManyConnections` |
| [security-incident.md](security-incident.md) | `LoginBruteForceSuspected`, scanner findings, leaked secret |
| [backup-and-restore.md](backup-and-restore.md) | Data loss, corruption, DR drill (RPO/RTO) |
| [deployment-rollback.md](deployment-rollback.md) | Bad release |
| [chaos-experiments.md](chaos-experiments.md) | Planned game days |
