# Presentation outline (15–18 slides, ~15 minutes + demo)

| # | Slide | Content | Visual |
|---|---|---|---|
| 1 | Title | DevSecOps360: secure, automated, observable, self-healing delivery | Logo + your name/guide |
| 2 | The problem | "Works on my machine" ≠ production. Delivery speed vs safety; DORA's 4 metrics | Before/after sketch |
| 3 | Objectives | The 10 objectives (report §1.3), condensed to 5 icons | Icon row |
| 4 | Architecture | Context diagram: dev → GitHub → Actions → GHCR → K8s → users; observability loop | `architecture.md` §1 |
| 5 | The application | React + FastAPI + PostgreSQL; JWT + RBAC; analytics | Screenshots 02, 03, 05 |
| 6 | CI pipeline | ci.yml jobs, quality gates (coverage 85 %, lint, SAST), E2E on Compose | Pipeline diagram §3 |
| 7 | DevSecOps | Shift-left controls table; STRIDE summary (17 threats → mitigations → tests) | Threat-model DFD |
| 8 | Supply chain | build → Trivy gate → SBOM → push + provenance → cosign sign/verify | Chain diagram |
| 9 | Containers | Multi-stage, non-root, read-only, healthchecks; Compose profiles for 8 GB | Image-size and RAM table |
| 10 | Kubernetes | Namespace security layers: PSA restricted, NetworkPolicies, RBAC, HPA, PDB, quotas | K8s diagram §4 |
| 11 | IaC | Terraform modules/environments; Ansible roles; "cluster is cattle" | Module tree |
| 12 | **Blue-green** | Two colours, preview service, selector switch, auto-rollback | `blue-green.md` diagram, then **LIVE DEMO** |
| 13 | Observability & SRE | SLIs/SLOs (99.5 %, p95 < 300 ms), error budget policy, burn-rate alerts | Grafana screenshot |
| 14 | Performance | Baseline vs stress before/after (39.6 % → 0.67 % errors, 2.7 → 50 req/s); root cause | Bar chart from performance report |
| 15 | Resilience & DR | Probes semantics, chaos experiments, backup + automated restore verification, RPO/RTO | Experiment table |
| 16 | Results | Test counts, coverage, scan results, validation matrix | `test-results.md` table |
| 17 | Limitations & future work | Honest list + roadmap (Kyverno, canary, OTel, PG HA) | — |
| 18 | Conclusion & Q&A | 3 key takeaways | — |

**Speaker tips**
- Lead with the *why* on every slide (the problem a tool solves), then the *what*.
- Quote real numbers. Examiners trust measured results with stated conditions.
- Have backup screenshots of every demo step in case the laptop struggles.
- Pre-warm everything 10 minutes before (Compose up or kind deployed, images loaded).
