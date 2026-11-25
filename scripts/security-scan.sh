#!/usr/bin/env bash
# Run the same security scans as CI, locally (needs Docker; images are pulled once).
# Reports go to reports/security/. Exit code is non-zero if any gate fails.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
mkdir -p reports/security
TRIVY=aquasec/trivy:0.58.1
GITLEAKS=ghcr.io/gitleaks/gitleaks:v8.21.2
rc=0
step() { printf '\n\033[1;34m== %s ==\033[0m\n' "$*"; }

step "Secrets (gitleaks, full git history)"
docker run --rm -v "$PWD:/repo" $GITLEAKS detect --source /repo --config /repo/security/gitleaks.toml \
  --redact --report-path /repo/reports/security/gitleaks.json || rc=1

step "Dependencies + secrets + misconfig (Trivy fs)"
docker run --rm -v "$PWD:/src" -w /src $TRIVY fs --config security/trivy.yaml --exit-code 1 . \
  | tee reports/security/trivy-fs.txt || rc=1

step "IaC misconfiguration (Trivy config: Dockerfiles, K8s, Terraform, Compose)"
docker run --rm -v "$PWD:/src" -w /src $TRIVY config --severity HIGH,CRITICAL \
  --ignorefile security/.trivyignore.yaml --exit-code 1 . | tee reports/security/trivy-iac.txt || rc=1

step "Python SAST (bandit) + CVEs (pip-audit)"
(cd apps/backend && bandit -r app -c pyproject.toml -ll -f txt -o ../../reports/security/bandit.txt; cat ../../reports/security/bandit.txt) || rc=1
pip-audit -r apps/backend/requirements.txt | tee reports/security/pip-audit.txt || rc=1

step "npm audit (production deps)"
(cd apps/frontend && npm audit --omit=dev --audit-level=high) | tee reports/security/npm-audit.txt || rc=1

if docker image inspect devsecops360-backend:local >/dev/null 2>&1; then
  step "Container images (Trivy image) + SBOM"
  for c in backend frontend; do
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD:/src" $TRIVY image \
      --severity HIGH,CRITICAL --ignore-unfixed "devsecops360-$c:local" | tee "reports/security/trivy-image-$c.txt"
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD:/src" $TRIVY image \
      --format cyclonedx --output "/src/reports/security/sbom-$c.cdx.json" "devsecops360-$c:local"
  done
fi

echo; [ $rc -eq 0 ] && echo "ALL SECURITY GATES PASSED" || echo "ONE OR MORE SECURITY GATES FAILED (see reports/security/)"
exit $rc
