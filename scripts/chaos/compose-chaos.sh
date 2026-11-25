#!/usr/bin/env bash
# Laptop-friendly chaos experiments on the Docker Compose stack (no Kubernetes).
#   ./scripts/chaos/compose-chaos.sh kill-backend   # restart policy self-heals
#   ./scripts/chaos/compose-chaos.sh db-outage      # readiness turns 503, recovers
set -euo pipefail
cd "$(dirname "$0")/../.."
URL="${URL:-http://localhost:8080}"

wait_status() { # wait_status <path> <code> <timeout>
  for _ in $(seq 1 "$3"); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' "$URL$1")" = "$2" ] && return 0; sleep 1
  done; return 1
}

case "${1:-}" in
  kill-backend)
    echo "steady state: $(curl -s $URL/health/ready)"
    t0=$(date +%s)
    # SIGKILL PID 1 inside the container -> container exits -> Docker restarts it
    docker compose kill -s SIGKILL backend
    wait_status /health/ready 200 90 || { echo '{"experiment":"kill-backend","result":"fail"}'; exit 1; }
    echo "{\"experiment\":\"kill-backend\",\"result\":\"pass\",\"recovery_seconds\":$(( $(date +%s) - t0 ))}"
    ;;
  db-outage)
    t0=$(date +%s)
    docker compose stop db
    wait_status /health/ready 503 30 && echo "backend reports 503 not-ready after $(( $(date +%s) - t0 ))s (fails fast)"
    docker compose start db
    t1=$(date +%s)
    wait_status /health/ready 200 90 || { echo '{"experiment":"db-outage","result":"fail"}'; exit 1; }
    echo "{\"experiment\":\"db-outage\",\"result\":\"pass\",\"recover_seconds\":$(( $(date +%s) - t1 )),\"backend_restarted\":false}"
    ;;
  *) echo "usage: $0 kill-backend|db-outage"; exit 2 ;;
esac
