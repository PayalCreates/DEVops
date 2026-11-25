#!/usr/bin/env bash
# ./load-testing/run.sh <smoke|baseline|stress|soak> [host]
set -euo pipefail
cd "$(dirname "$0")/.."
profile="${1:-baseline}"; host="${2:-http://localhost:8080}"
case "$profile" in
  smoke)    u=5;   r=5;  t=30s ;;
  baseline) u=25;  r=5;  t=3m  ;;
  stress)   u=100; r=10; t=5m  ;;
  soak)     u=25;  r=5;  t=30m ;;
  *) echo "unknown profile $profile"; exit 2 ;;
esac
mkdir -p load-testing/results
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
locust -f load-testing/locustfile.py --host "$host" --headless -u "$u" -r "$r" -t "$t" \
  --csv "load-testing/results/${profile}-${stamp}" --html "load-testing/results/${profile}-${stamp}.html" \
  --only-summary
