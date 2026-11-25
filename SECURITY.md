# Security Policy

## Supported versions
Only the latest release on `main` receives security fixes.

## Reporting a vulnerability
Please **do not open a public issue**. Use GitHub's
[private vulnerability reporting](../../security/advisories/new) for this repository.
You will get an acknowledgement within 72 hours and a fix or mitigation plan within 14 days
for HIGH/CRITICAL issues.

## What we do
| Control | Where |
|---|---|
| Secret scanning (gitleaks, pre-commit + CI, full history) | `security/gitleaks.toml`, `.github/workflows/security.yml` |
| SAST (Semgrep, Bandit, CodeQL) | `security/semgrep-rules.yml`, `ci.yml`, `codeql.yml` |
| Dependency scanning (pip-audit, npm audit, Trivy, Dependabot) | `security.yml`, `.github/dependabot.yml` |
| Container image scanning, CRITICAL gate | `delivery.yml` |
| SBOM (SPDX + CycloneDX) per image | `delivery.yml` |
| Keyless image signing + SBOM attestation (cosign / Sigstore) | `delivery.yml` |
| IaC misconfiguration scanning | `security.yml` (Trivy config) |
| Runtime hardening (non-root, read-only FS, dropped caps, seccomp) | `docker-compose.yml`, `kubernetes/base/` |
| Network segmentation (default-deny NetworkPolicies) | `kubernetes/base/networkpolicy.yaml` |

Full details: [docs/security/security-guide.md](docs/security/security-guide.md) and the
[threat model](docs/security/threat-model.md).
