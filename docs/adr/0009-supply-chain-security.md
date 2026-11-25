# ADR-0009: Software supply-chain security

**Status:** Accepted

## Decision
Every image that reaches the registry has been:
1. **built** from a pinned base image and lockfile (`npm ci`, pinned `requirements.txt`);
2. **scanned** by Trivy *before push*, where any fixable CRITICAL CVE fails the pipeline;
3. **described** by SBOMs in SPDX and CycloneDX formats, uploaded as artifacts and attested;
4. **pushed** with SLSA provenance (`provenance: mode=max`);
5. **signed** keylessly with cosign through GitHub OIDC and Sigstore, and **verified** in the same job.

Source-side controls: gitleaks, Semgrep with custom rules, CodeQL, Bandit, pip-audit,
npm audit, Dependency Review on PRs, Dependabot, and pinned GitHub Action major versions.
Security scanners run from versioned container images rather than third-party
marketplace actions where practical, which reduces the risk of a compromised action tag.

## Consequences
+ We can answer "what is in this image, who built it, from which commit?" for every deployment.
+ A cluster admission policy (Kyverno `verifyImages` or Sigstore policy-controller) can require signatures. This is documented as the next step.
− Scans add about 1–2 minutes per pipeline run.
