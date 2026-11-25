# Incident response

## Severity
| SEV | Definition | Response |
|---|---|---|
| SEV1 | Full outage, data loss, or active security breach | Page immediately; all hands; updates every 30 min |
| SEV2 | Major degradation (error budget fast burn, key feature broken) | Page on-call; updates hourly |
| SEV3 | Minor degradation, workaround exists | Ticket; next business day |

## Roles (one person may hold several in a small team)
- **Incident Commander (IC):** coordinates and decides; does not debug.
- **Ops lead:** hands on keyboard, executes runbooks.
- **Comms lead:** status updates to stakeholders.
- **Scribe:** timestamped timeline in the incident doc.

## Process
1. **Detect:** an alert fires (Alertmanager) or a user report arrives. Acknowledge within 5 min.
2. **Triage:** assign a SEV, open an incident channel or doc, name the IC.
3. **Mitigate first:** roll back (`deployment/rollback/rollback.sh`), scale out, fail over, or restore. Don't hunt for root cause while users are down.
4. **Verify:** smoke tests pass; SLI dashboards are back within SLO for 15 min.
5. **Resolve and communicate.**
6. **Postmortem** within 5 working days. It is blameless and uses the template below.

## First 5 minutes checklist
```bash
NS=devsecops360-dev
./deployment/scripts/status.sh                        # which colour is live, are pods ready?
kubectl -n $NS get pods -o wide; kubectl -n $NS get events --sort-by=.lastTimestamp | tail -20
kubectl -n $NS logs deploy/backend-$(kubectl -n $NS get svc backend -o jsonpath='{.spec.selector.devsecops360/color}') --tail=100
# Grafana → "DevSecOps360 — Service Overview & SLOs"; Loki: {service="backend", level="ERROR"}
# Was there a deploy in the last hour? → roll back first, ask questions later.
```

## Postmortem template
```markdown
# Postmortem: <title>   (SEV?, <date>)
## Summary            — 2-3 sentences, user impact, duration
## Impact             — requests failed, users affected, error budget consumed
## Timeline (UTC)     — detection, escalation, mitigation, resolution
## Root cause         — the technical chain of events ("5 whys")
## What went well / what went badly / where we got lucky
## Action items       — owner, due date, ticket; prevent / detect / mitigate
```
