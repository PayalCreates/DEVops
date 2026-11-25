#!/usr/bin/env bash
# =============================================================================
# Blue-Green deployment of the backend with validation and automatic rollback.
#
#   NAMESPACE=devsecops360-dev ./deployment/scripts/blue-green-deploy.sh <backend-image>
#   e.g. ./deployment/scripts/blue-green-deploy.sh devsecops360-backend:v1.1.0
#
# Steps
#   1. detect ACTIVE colour from the `backend` Service selector; IDLE = the other
#   2. run DB migrations with the NEW image (must be backwards compatible)
#   3. roll the NEW image onto the IDLE colour and scale it to the active size
#   4. smoke-test IDLE through `backend-preview` (zero user traffic so far)
#   5. SWITCH: patch `backend` selector → IDLE (atomic, instant)
#   6. verify through the public path (frontend → backend); auto-rollback on failure
#   7. keep the old colour running for instant manual rollback (SCALE_DOWN_OLD=true to free RAM)
# =============================================================================
source "$(dirname "$0")/lib.sh"
require kubectl

NEW_IMAGE="${1:?usage: blue-green-deploy.sh <backend-image>}"
SCALE_DOWN_OLD="${SCALE_DOWN_OLD:-false}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"

ACTIVE="$(active_color)"; [ -n "$ACTIVE" ] || fail "cannot read active colour from svc/backend"
IDLE="$(other_color "$ACTIVE")"
REPLICAS="$($KUBECTL get deploy "backend-$ACTIVE" -o jsonpath='{.spec.replicas}')"
[ "${REPLICAS:-0}" -ge 1 ] || REPLICAS=1
OLD_IMAGE="$($KUBECTL get deploy "backend-$ACTIVE" -o jsonpath='{.spec.template.spec.containers[0].image}')"
T0=$(date +%s)

log "namespace=$NAMESPACE active=$ACTIVE ($OLD_IMAGE) → deploying $NEW_IMAGE to $IDLE"

# --- 2. migrations ------------------------------------------------------------
log "running database migrations with the new image"
$KUBECTL delete job db-migrate --ignore-not-found --wait=true >/dev/null
# The Job template lives in kubernetes/base; only the image is release-specific.
sed "s#image: devsecops360-backend\$#image: $NEW_IMAGE#" "$REPO_ROOT/kubernetes/base/migrate-job.yaml" \
  | $KUBECTL apply -f - >/dev/null
$KUBECTL wait --for=condition=complete job/db-migrate --timeout=300s >/dev/null \
  || { $KUBECTL logs job/db-migrate --tail=50 || true; fail "migration job failed — nothing switched"; }
ok "migrations applied"

# --- 3. roll out to idle ------------------------------------------------------
log "updating backend-$IDLE to $NEW_IMAGE (replicas=$REPLICAS)"
$KUBECTL set image "deploy/backend-$IDLE" backend="$NEW_IMAGE" >/dev/null
$KUBECTL scale "deploy/backend-$IDLE" --replicas="$REPLICAS" >/dev/null
$KUBECTL annotate "deploy/backend-$IDLE" kubernetes.io/change-cause="blue-green: $NEW_IMAGE" --overwrite >/dev/null
$KUBECTL rollout status "deploy/backend-$IDLE" --timeout="$ROLLOUT_TIMEOUT" \
  || fail "rollout of backend-$IDLE did not become ready — traffic still on $ACTIVE"
ok "backend-$IDLE ready"

# --- 4. pre-switch validation via preview service -----------------------------
log "smoke testing $IDLE via backend-preview (no user traffic yet)"
run_smoke "http://backend-preview:8000" "$IDLE" "$NEW_IMAGE" \
  || fail "pre-switch smoke test FAILED on $IDLE — traffic still on $ACTIVE (nothing to roll back)"
ok "pre-switch smoke test passed"

# --- 5. switch -----------------------------------------------------------------
log "SWITCHING traffic $ACTIVE → $IDLE"
switch_traffic "$IDLE"
T_SWITCH=$(date +%s)
ok "backend Service now selects $IDLE"

# --- 6. post-switch verification through the public path ----------------------
sleep 3 # allow kube-proxy to program the new endpoints
if ! run_smoke "http://frontend:8080" "$IDLE" "$NEW_IMAGE"; then
  log "post-switch verification FAILED — automatic rollback to $ACTIVE"
  switch_traffic "$ACTIVE"
  run_smoke "http://frontend:8080" "$ACTIVE" "$OLD_IMAGE" || fail "rollback verification failed — page on-call!"
  fail "deployment rolled back; $ACTIVE ($OLD_IMAGE) is serving"
fi
ok "post-switch verification passed"

# --- 7. old colour ---------------------------------------------------------------
if [ "$SCALE_DOWN_OLD" = "true" ]; then
  $KUBECTL scale "deploy/backend-$ACTIVE" --replicas=0 >/dev/null
  log "scaled backend-$ACTIVE to 0 (rollback now needs a scale-up: ~20s)"
else
  log "backend-$ACTIVE kept running for instant rollback: deployment/rollback/rollback.sh"
fi

echo "{\"event\":\"blue_green_deploy\",\"result\":\"success\",\"namespace\":\"$NAMESPACE\",\"from\":\"$ACTIVE\",\"to\":\"$IDLE\",\"image\":\"$NEW_IMAGE\",\"total_seconds\":$(( $(date +%s) - T0 )),\"switch_epoch\":$T_SWITCH}"
