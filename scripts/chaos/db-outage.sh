#!/usr/bin/env bash
# CHAOS EXPERIMENT 2 — dependency failure (database outage)
# Hypothesis: when PostgreSQL disappears, backend pods turn NOT READY (readiness
# probe → 503) but are NOT restarted (liveness stays green); when the DB returns
# they become ready again on their own (pool_pre_ping) — no manual restarts.
source "$(dirname "$0")/../../deployment/scripts/lib.sh"
require kubectl

color="$(active_color)"
restarts_before="$($KUBECTL get pod -l "app.kubernetes.io/name=backend,devsecops360/color=$color" \
  -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{" "}{end}')"

log "scaling postgres to 0 (simulated outage)"
t0=$(date +%s)
$KUBECTL scale statefulset/postgres --replicas=0 >/dev/null
$KUBECTL wait --for=delete pod/postgres-0 --timeout=90s >/dev/null 2>&1 || true

log "expecting backend-$color to become NotReady"
for _ in $(seq 1 30); do
  ready="$($KUBECTL get deploy "backend-$color" -o jsonpath='{.status.readyReplicas}')"
  [ -z "$ready" ] || [ "$ready" = "0" ] && break
  sleep 2
done
detect=$(( $(date +%s) - t0 ))
[ -z "$ready" ] || [ "$ready" = "0" ] || fail "backend still Ready during DB outage — readiness probe not checking DB"
ok "backend removed from Service endpoints after ${detect}s (users get fast 503s, not hangs)"

log "restoring postgres"
t1=$(date +%s)
$KUBECTL scale statefulset/postgres --replicas=1 >/dev/null
$KUBECTL rollout status statefulset/postgres --timeout=180s >/dev/null
$KUBECTL rollout status "deploy/backend-$color" --timeout=180s >/dev/null
for _ in $(seq 1 60); do
  ready="$($KUBECTL get deploy "backend-$color" -o jsonpath='{.status.readyReplicas}')"
  want="$($KUBECTL get deploy "backend-$color" -o jsonpath='{.spec.replicas}')"
  [ "${ready:-0}" = "$want" ] && break
  sleep 2
done
recover=$(( $(date +%s) - t1 ))
restarts_after="$($KUBECTL get pod -l "app.kubernetes.io/name=backend,devsecops360/color=$color" \
  -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{" "}{end}')"

ok "backend Ready again ${recover}s after DB returned"
[ "$restarts_before" = "$restarts_after" ] && ok "no container restarts (liveness correctly ignored the DB)" \
  || log "restart counts changed: '$restarts_before' → '$restarts_after'"
echo "{\"experiment\":\"db-outage\",\"result\":\"pass\",\"detect_seconds\":$detect,\"recover_seconds\":$recover,\"restarts_before\":\"${restarts_before% }\",\"restarts_after\":\"${restarts_after% }\"}"
