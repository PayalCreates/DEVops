#!/usr/bin/env bash
# Create the `backend-secrets` Secret with strong random values when you are NOT
# using Terraform (Terraform's app-namespace module does the same thing).
# Idempotent: an existing secret is left untouched unless ROTATE=true.
#   NAMESPACE=devsecops360-dev ./deployment/scripts/create-secrets.sh
source "$(dirname "$0")/lib.sh"
require kubectl openssl

kubectl get ns "$NAMESPACE" >/dev/null 2>&1 || kubectl apply -f "$REPO_ROOT/kubernetes/overlays/${OVERLAY:-development}/namespace.yaml"

if $KUBECTL get secret backend-secrets >/dev/null 2>&1 && [ "${ROTATE:-false}" != "true" ]; then
  ok "backend-secrets already exists in $NAMESPACE (set ROTATE=true to replace)"
  exit 0
fi

admin_pw="Adm-$(openssl rand -hex 8)"
demo_pw="Demo-$(openssl rand -hex 6)"
$KUBECTL create secret generic backend-secrets \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)" \
  --from-literal=JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=ADMIN_PASSWORD="$admin_pw" \
  --from-literal=DEMO_USER_PASSWORD="$demo_pw" \
  --dry-run=client -o yaml | $KUBECTL apply -f - >/dev/null

ok "backend-secrets created in $NAMESPACE"
echo "Admin login : admin@devsecops360.dev / (run: kubectl -n $NAMESPACE get secret backend-secrets -o jsonpath='{.data.ADMIN_PASSWORD}' | base64 -d)"
