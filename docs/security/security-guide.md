# Security Guide

How security is built into each layer, and how to run every check yourself.

## 1. Shift-left: before code is pushed
```powershell
pip install pre-commit; pre-commit install   # gitleaks, ruff, yamllint, terraform fmt, private-key detection
```

## 2. In CI (every PR)
| Check | Tool | Gate |
|---|---|---|
| Secrets in code or history | gitleaks (`security/gitleaks.toml`) | any finding fails |
| Python SAST | Bandit, Semgrep (`p/python`, `p/fastapi`, custom rules), CodeQL | medium+ (Bandit `-ll`), Semgrep ERROR |
| TypeScript SAST | ESLint security rules, Semgrep `p/typescript`/`p/react`, CodeQL | errors fail |
| Dependency CVEs | pip-audit, npm audit (prod deps), Trivy fs, Dependency Review | HIGH+ fixable fails |
| IaC misconfiguration | Trivy config (Dockerfiles, K8s, Terraform, Compose) | HIGH+ fails |
| K8s policy | `scripts/validate/k8s_policy_check.py` | any violation fails |
| Image CVEs | Trivy image (before push) | fixable CRITICAL fails |
| SBOM | Trivy → SPDX + CycloneDX | artifact + cosign attestation |
| Signing | cosign keyless (Sigstore, GitHub OIDC) | verify step must pass |

All SARIF results appear under **GitHub → Security → Code scanning**.

## 3. Run locally
```powershell
.\scripts\security-scan.ps1          # Windows (Docker Desktop)
./scripts/security-scan.sh           # Linux/WSL, writes reports/security/
```
Verify a published image signature:
```bash
cosign verify ghcr.io/<owner>/devsecops360-backend@sha256:<digest> \
  --certificate-identity-regexp '^https://github.com/<owner>/devsecops360/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
cosign download attestation ghcr.io/<owner>/devsecops360-backend@sha256:<digest> | jq -r .payload | base64 -d | jq .predicateType
```

## 4. Application controls
- Password policy: 8–72 characters with upper case, lower case and a digit (bcrypt's 72-byte limit is enforced rather than silently truncating).
- JWT: HS256 pinned, `exp`/`iat`/`iss` required, minimum 32-character secret enforced at startup outside development (`Settings.validate_production_safety`).
- Security headers on API and SPA: CSP, `X-Frame-Options: DENY`, `nosniff`, HSTS, Referrer-Policy, Permissions-Policy, COOP.
- CORS: explicit origin allow-list, no credentials, fixed methods and headers.
- `/docs` and OpenAPI disabled in production.

## 5. Container & runtime controls
| Control | Compose | Kubernetes |
|---|---|---|
| Non-root user | UID 10001 (backend), 101 (nginx) | `runAsNonRoot`, fixed UIDs; postgres runs as UID 70 |
| Read-only root FS | `read_only: true` + tmpfs | `readOnlyRootFilesystem: true` + emptyDir |
| Capabilities | `cap_drop: ALL` | `drop: [ALL]` |
| Privilege escalation | `no-new-privileges` | `allowPrivilegeEscalation: false` |
| Seccomp | Docker default | `RuntimeDefault` |
| Network | `data` network `internal: true`; DB not published | default-deny NetworkPolicies |
| Admission | — | Pod Security Admission `restricted` |
| API access | — | `automountServiceAccountToken: false`; namespaced RBAC |

## 6. Responding to a finding
1. Triage severity and exploitability (is the vulnerable function reachable?).
2. Fix by upgrading the dependency or base image. Dependabot usually opens the PR.
3. If it is a false positive or not reachable, add a scoped entry to `security/.trivyignore.yaml` with a `statement` and an `expired_at` date. Never ignore globally.
4. Record the decision in the PR.

See also the [threat model](threat-model.md) and [security incident runbook](../runbooks/security-incident.md).
