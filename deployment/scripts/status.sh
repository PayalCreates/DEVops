#!/usr/bin/env bash
# Show which colour is live, images per colour and readiness.
source "$(dirname "$0")/lib.sh"
require kubectl
active="$(active_color)"
printf '%-8s %-7s %-9s %s\n' COLOR ACTIVE READY IMAGE
for c in blue green; do
  img=$($KUBECTL get deploy "backend-$c" -o jsonpath='{.spec.template.spec.containers[0].image}')
  rdy=$($KUBECTL get deploy "backend-$c" -o jsonpath='{.status.readyReplicas}/{.spec.replicas}')
  printf '%-8s %-7s %-9s %s\n' "$c" "$([ "$c" = "$active" ] && echo '  ★' || echo '')" "${rdy}" "$img"
done
echo; $KUBECTL get svc backend backend-preview -o custom-columns='SERVICE:.metadata.name,SELECTS:.spec.selector.devsecops360/color'
