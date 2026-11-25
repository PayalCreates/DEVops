#!/usr/bin/env bash
# Build images, load them into kind, apply the overlay, run migrations, wait.
#   bash deployment/scripts/deploy-k8s.sh                 # development overlay, tag "local"
#   TAG=v1.1.0 bash deployment/scripts/deploy-k8s.sh
source "$(dirname "$0")/lib.sh"
require docker kind kubectl

CLUSTER="${CLUSTER:-devsecops360}"
OVERLAY="${OVERLAY:-development}"
TAG="${TAG:-local}"
cd "$REPO_ROOT" || exit 1

kind get clusters | grep -qx "$CLUSTER" || fail "kind cluster '$CLUSTER' not found — run: cd terraform/environments/local && terraform apply"
kubectl config use-context "kind-$CLUSTER" >/dev/null

if [ "${SKIP_BUILD:-false}" != "true" ]; then
  log "building images (tag $TAG)"
  docker build -f docker/backend.Dockerfile -t "devsecops360-backend:$TAG" apps/backend
  docker build -f docker/frontend.Dockerfile -t "devsecops360-frontend:$TAG" apps/frontend
fi
log "loading images into kind (no registry needed)"
kind load docker-image --name "$CLUSTER" "devsecops360-backend:$TAG" "devsecops360-frontend:$TAG"
docker pull -q postgres:16-alpine >/dev/null && kind load docker-image --name "$CLUSTER" postgres:16-alpine

bash "$SCRIPT_DIR/create-secrets.sh"

log "applying overlay $OVERLAY"
# Jobs are immutable: remove the previous migration job so this release re-runs it
$KUBECTL delete job db-migrate --ignore-not-found >/dev/null 2>&1 || true
kubectl kustomize "kubernetes/overlays/$OVERLAY" \
  | sed "s#image: devsecops360-backend:local#image: devsecops360-backend:$TAG#; s#image: devsecops360-frontend:local#image: devsecops360-frontend:$TAG#" \
  | kubectl apply -f -

log "waiting for postgres, migrations, backend and frontend"
$KUBECTL rollout status statefulset/postgres --timeout=300s
$KUBECTL wait --for=condition=complete job/db-migrate --timeout=300s
$KUBECTL rollout status "deploy/backend-$(active_color)" --timeout=300s
$KUBECTL rollout status deploy/frontend --timeout=180s
ok "deployed. Open http://devsecops360.localtest.me:8088"
$KUBECTL get pods -o wide
