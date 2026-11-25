#!/usr/bin/env bash
# Shared helpers for deployment scripts.
set -euo pipefail

log()  { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
ok()   { printf '\033[1;32m[%s] ✔ %s\033[0m\n' "$(date +%H:%M:%S)" "$*"; }
fail() { printf '\033[1;31m[%s] ✘ %s\033[0m\n' "$(date +%H:%M:%S)" "$*" >&2; exit 1; }

require() { for c in "$@"; do command -v "$c" >/dev/null || fail "required command not found: $c"; done; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export REPO_ROOT; REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NAMESPACE="${NAMESPACE:-devsecops360-dev}"
KUBECTL="kubectl -n $NAMESPACE"

active_color() {
  $KUBECTL get svc backend -o jsonpath='{.spec.selector.devsecops360/color}'
}

other_color() { [ "$1" = "blue" ] && echo green || echo blue; }

# Run smoke_check.py inside the cluster as a short-lived, restricted pod.
#   run_smoke <base-url> <expected-color> <image>
run_smoke() {
  local base="$1" color="$2" image="$3" name
  name="smoke-$(date +%s)"
  $KUBECTL create configmap smoke-check --from-file="$SCRIPT_DIR/smoke_check.py" \
    --dry-run=client -o yaml | $KUBECTL apply -f - >/dev/null
  cat <<EOF | $KUBECTL apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: $name
  labels: { devsecops360/role: smoke-test }
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: smoke
      image: $image
      imagePullPolicy: IfNotPresent
      command: ["python", "/smoke/smoke_check.py", "$base", "$color"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: { drop: ["ALL"] }
      resources:
        requests: { cpu: 10m, memory: 32Mi }
        limits: { cpu: 200m, memory: 96Mi }
      volumeMounts: [{ name: smoke, mountPath: /smoke }]
  volumes:
    - name: smoke
      configMap: { name: smoke-check }
EOF
  local phase=""
  for _ in $(seq 1 60); do
    phase=$($KUBECTL get pod "$name" -o jsonpath='{.status.phase}' 2>/dev/null || true)
    [[ "$phase" == "Succeeded" || "$phase" == "Failed" ]] && break
    sleep 2
  done
  $KUBECTL logs "$name" || true
  $KUBECTL delete pod "$name" --wait=false >/dev/null 2>&1 || true
  [ "$phase" = "Succeeded" ]
}

switch_traffic() {
  local to="$1" from
  from="$(other_color "$to")"
  # Both patches are tiny and applied back to back; the active switch is atomic.
  $KUBECTL patch svc backend --type merge -p \
    "{\"metadata\":{\"annotations\":{\"devsecops360/active-color\":\"$to\",\"devsecops360/switched-at\":\"$(date -u +%FT%TZ)\"}},\"spec\":{\"selector\":{\"devsecops360/color\":\"$to\"}}}" >/dev/null
  $KUBECTL patch svc backend-preview --type merge -p \
    "{\"spec\":{\"selector\":{\"devsecops360/color\":\"$from\"}}}" >/dev/null
}
