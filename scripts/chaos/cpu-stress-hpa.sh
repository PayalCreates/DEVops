#!/usr/bin/env bash
# CHAOS EXPERIMENT 3 — load spike / autoscaling
# Hypothesis: sustained load raises backend CPU above 70% and the HPA scales the
# active colour out (up to maxReplicas), then back in after the load stops.
# Requires metrics-server (installed by Terraform). Load is generated in-cluster.
source "$(dirname "$0")/../../deployment/scripts/lib.sh"
require kubectl
DURATION="${DURATION:-120}"
color="$(active_color)"
image="$($KUBECTL get deploy "backend-$color" -o jsonpath='{.spec.template.spec.containers[0].image}')"

log "HPA before:"; $KUBECTL get hpa "backend-$color"
cat <<EOF | $KUBECTL apply -f - >/dev/null
apiVersion: batch/v1
kind: Job
metadata:
  name: load-spike
spec:
  parallelism: 2
  backoffLimit: 0
  activeDeadlineSeconds: $(( DURATION + 30 ))
  template:
    metadata:
      labels: { devsecops360/role: smoke-test }
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext: { runAsNonRoot: true, runAsUser: 10001, seccompProfile: { type: RuntimeDefault } }
      containers:
        - name: load
          image: $image
          imagePullPolicy: IfNotPresent
          command:
            - python
            - -c
            - |
              import time, urllib.request, concurrent.futures as cf
              end = time.time() + $DURATION
              def hit(_):
                  n = 0
                  while time.time() < end:
                      try: urllib.request.urlopen("http://backend:8000/api/v1/version", timeout=5).read(); n += 1
                      except Exception: pass
                  return n
              with cf.ThreadPoolExecutor(16) as ex: print("requests:", sum(ex.map(hit, range(16))))
          securityContext: { allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: { drop: ["ALL"] } }
          resources: { requests: { cpu: 100m, memory: 64Mi }, limits: { cpu: 500m, memory: 128Mi } }
EOF
max=0
for _ in $(seq 1 $(( DURATION / 10 ))); do
  sleep 10
  cur="$($KUBECTL get hpa "backend-$color" -o jsonpath='{.status.currentReplicas}')"
  cpu="$($KUBECTL get hpa "backend-$color" -o jsonpath='{.status.currentMetrics[0].resource.current.averageUtilization}')"
  log "replicas=$cur cpu=${cpu:-?}%"
  [ "${cur:-0}" -gt "$max" ] && max="$cur"
done
$KUBECTL delete job load-spike --wait=false >/dev/null
echo "{\"experiment\":\"cpu-stress-hpa\",\"color\":\"$color\",\"max_replicas_observed\":$max}"
[ "$max" -gt 1 ] && ok "HPA scaled out to $max replicas" || log "HPA did not scale (check metrics-server: kubectl top pods)"
