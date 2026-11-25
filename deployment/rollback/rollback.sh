#!/usr/bin/env bash
# Instant blue-green rollback: point the `backend` Service back at the other colour.
#   NAMESPACE=devsecops360-dev ./deployment/rollback/rollback.sh
# If the previous colour was scaled to 0, it is scaled up first (adds ~20 s).
source "$(dirname "$0")/../scripts/lib.sh"
require kubectl

CURRENT="$(active_color)"
TARGET="$(other_color "$CURRENT")"
T0=$(date +%s)
log "rollback requested: $CURRENT → $TARGET (namespace $NAMESPACE)"

ready="$($KUBECTL get deploy "backend-$TARGET" -o jsonpath='{.status.readyReplicas}')"
if [ "${ready:-0}" -lt 1 ]; then
  replicas="$($KUBECTL get deploy "backend-$CURRENT" -o jsonpath='{.spec.replicas}')"
  log "backend-$TARGET has no ready pods — scaling to ${replicas:-1}"
  $KUBECTL scale "deploy/backend-$TARGET" --replicas="${replicas:-1}" >/dev/null
  $KUBECTL rollout status "deploy/backend-$TARGET" --timeout=180s || fail "previous colour failed to start"
fi

image="$($KUBECTL get deploy "backend-$TARGET" -o jsonpath='{.spec.template.spec.containers[0].image}')"
switch_traffic "$TARGET"
ok "traffic switched to $TARGET ($image)"

sleep 3
run_smoke "http://frontend:8080" "$TARGET" "$image" || fail "rollback verification failed — investigate immediately"
echo "{\"event\":\"rollback\",\"result\":\"success\",\"namespace\":\"$NAMESPACE\",\"from\":\"$CURRENT\",\"to\":\"$TARGET\",\"image\":\"$image\",\"seconds\":$(( $(date +%s) - T0 ))}"
