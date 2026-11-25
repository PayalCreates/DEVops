#!/usr/bin/env bash
# CHAOS EXPERIMENT 1 — pod failure / self-healing
# Hypothesis: if an active backend pod is killed, the Deployment controller
# replaces it and the service recovers within 60 s without manual action.
source "$(dirname "$0")/../../deployment/scripts/lib.sh"
require kubectl

color="$(active_color)"
pod="$($KUBECTL get pod -l "app.kubernetes.io/name=backend,devsecops360/color=$color" \
        -o jsonpath='{.items[0].metadata.name}')"
[ -n "$pod" ] || fail "no active backend pod found"
before="$($KUBECTL get pod -l "devsecops360/color=$color,app.kubernetes.io/name=backend" -o name | sort)"

log "steady state: $(echo "$before" | wc -l) ready pod(s) on $color; killing $pod (grace 0)"
t0=$(date +%s)
$KUBECTL delete pod "$pod" --grace-period=0 --force >/dev/null 2>&1

$KUBECTL rollout status "deploy/backend-$color" --timeout=120s >/dev/null
for _ in $(seq 1 60); do
  ready="$($KUBECTL get deploy "backend-$color" -o jsonpath='{.status.readyReplicas}')"
  want="$($KUBECTL get deploy "backend-$color" -o jsonpath='{.spec.replicas}')"
  [ "${ready:-0}" = "$want" ] && break
  sleep 1
done
recovery=$(( $(date +%s) - t0 ))
after="$($KUBECTL get pod -l "devsecops360/color=$color,app.kubernetes.io/name=backend" -o name | sort)"
[ "$before" != "$after" ] || fail "pod list unchanged — kill did not happen?"
[ "$recovery" -le 60 ] || fail "recovery took ${recovery}s (> 60s hypothesis)"
ok "self-healed: replacement pod ready in ${recovery}s"
echo "{\"experiment\":\"kill-pod\",\"result\":\"pass\",\"color\":\"$color\",\"killed\":\"$pod\",\"recovery_seconds\":$recovery}"
