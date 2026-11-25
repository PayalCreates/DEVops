# DevSecOps360: A Secure, Automated, Observable and Self-Healing Software Delivery Platform

**Capstone Project Report**

| | |
|---|---|
| Student | *‹Your name›* · *‹Roll number›* |
| Programme | *‹Degree / branch›* |
| Supervisor | *‹Guide name›* |
| Institution | *‹University›* |
| Date | *‹Submission date›* |

---

## Abstract
Modern software organisations compete on how quickly and safely they can turn a code
change into a reliable production service. This project designs and implements
**DevSecOps360**, an end-to-end delivery platform around a full-stack task-management
application (React/TypeScript, FastAPI, PostgreSQL). Every change passes automated
quality, security and infrastructure gates in GitHub Actions. Container images are
scanned, described by Software Bills of Materials (SBOMs) and cryptographically signed.
Deployments use a blue-green strategy on Kubernetes with pre-release validation and
automatic rollback. The platform is observable through Prometheus, Grafana and Loki, with
Service Level Objectives (SLOs) and burn-rate alerting, and it is resilient through health
probes, autoscaling, automated backups with restore verification, and controlled failure
experiments. Infrastructure is reproducible through Terraform and Ansible, and the whole
system is engineered to run on an 8 GB Windows laptop.

Evaluation combined 60 automated backend tests (97.9 % coverage, run against PostgreSQL 16),
20 frontend tests, 4 browser end-to-end tests, schema and policy validation of all Kubernetes
manifests, and load testing. Load testing exposed a connection-pool exhaustion bottleneck under
100 concurrent users (39.6 % errors, p95 59 s). After root-cause analysis and two targeted
fixes, the error rate fell to 0.67 % and p95 latency to 170 ms, an 18.5× throughput
improvement. The project shows that production-grade DevSecOps and SRE practices can be
applied rigorously, and measured honestly, with free and open-source tools on modest hardware.

**Keywords:** DevSecOps, CI/CD, Kubernetes, blue-green deployment, software supply chain,
SBOM, SRE, SLO, observability, infrastructure as code.

---

## 1. Introduction

### 1.1 Background
DevOps unifies development and operations through automation, shared ownership and fast
feedback. DevSecOps extends this by building security controls into every stage of the
pipeline rather than auditing at the end ("shift left"). Site Reliability Engineering (SRE)
adds a quantitative approach to reliability through SLIs, SLOs and error budgets. Research by
the DORA programme associates high delivery performance (deployment frequency, lead time,
change-failure rate, time to restore) with organisational performance, and these four
metrics are achievable only with a high degree of automation.

### 1.2 Problem statement
Student and small-team projects typically stop at "the application works on my machine".
They rarely show how software is *delivered*: how it is tested and secured automatically,
deployed without downtime, monitored against explicit objectives, recovered after failure,
and rebuilt from scratch. The challenge is to build such a platform end to end, with real
working automation rather than placeholder configuration, under tight hardware limits.

### 1.3 Objectives
1. Build a secure full-stack application with authentication, RBAC and analytics.
2. Automate build, test, security scanning and delivery with CI/CD.
3. Containerise all services following image-hardening best practices.
4. Deploy on Kubernetes with production-grade security and reliability controls.
5. Implement zero-downtime blue-green deployment with validation and automatic rollback.
6. Provision infrastructure and configuration reproducibly (Terraform, Ansible).
7. Secure the software supply chain (scanning, SBOM, signing, provenance).
8. Establish observability and SRE practices (metrics, logs, SLOs, alerting, runbooks).
9. Measure performance, find and fix bottlenecks, and verify recovery procedures.
10. Keep everything reproducible on an 8 GB Windows laptop with free tools.

### 1.4 Scope
In scope: the application, CI/CD, containers, a local Kubernetes cluster (kind), IaC, security
automation, observability, blue-green deployment, load testing, backup/restore and chaos
experiments. Out of scope: multi-region deployment, managed cloud services (documented as
optional), and an external identity provider.

---

## 2. Literature and technology review
- **Continuous delivery and DORA metrics.** The State of DevOps research identifies deployment frequency, lead time for changes, change-failure rate and time to restore service as predictors of software delivery performance. The platform targets all four: automated pipelines (frequency, lead time), pre-switch validation (change-failure rate), and one-command rollback (time to restore).
- **SRE (Google SRE book and workbook).** SLOs express reliability targets from the user's perspective. Error budgets balance velocity against risk. Multi-window, multi-burn-rate alerting reduces both missed incidents and false pages. These are implemented directly in the Prometheus rules.
- **Secure software development.** NIST SP 800-218 (SSDF) and the OWASP Top 10 inform the controls: input validation, broken-access-control prevention (ownership checks), cryptographic storage (bcrypt), security misconfiguration (hardened containers, PSA restricted) and vulnerable components (SCA scanning).
- **Supply-chain security.** SLSA defines levels of build integrity. Sigstore enables keyless signing tied to CI identity through OIDC. SBOM formats (SPDX, CycloneDX) make image contents auditable. The delivery pipeline produces SLSA provenance, both SBOM formats and cosign signatures.
- **Deployment strategies.** Rolling updates, blue-green and canary trade capacity, rollback speed and blast radius against each other. Blue-green offers instant rollback and pre-release testing on vanilla Kubernetes (ADR-0005).
- **Observability.** The RED method (Rate, Errors, Duration) for request-driven services; structured logging with correlation IDs; Prometheus/Grafana/Loki as an integrated open-source stack.

---

## 3. Methodology
The project followed an incremental, milestone-based approach with a verification gate at
every step: build a component, write automated checks for it, run them, fix defects, then
proceed. Architectural decisions were recorded as ADRs. Security was treated as a
functional requirement via a STRIDE threat model whose mitigations are linked to code and
tests. Performance work followed the scientific method: baseline → hypothesis →
change one variable → re-measure.

**Tooling selection criteria:** free/open-source, actively maintained (e.g. Traefik instead
of the retired ingress-nginx, Alloy instead of the end-of-life Promtail), low memory
footprint, and the same tool locally and in CI (kind in both).

---

## 4. System design

### 4.1 Architecture
See `docs/architecture/architecture.md` for the diagrams. The browser loads the SPA from an
unprivileged nginx container that also reverse-proxies `/api` to the FastAPI backend, giving a
single origin and a strict Content-Security-Policy. The backend is stateless (JWT), so any
replica of either blue-green colour can serve any request. PostgreSQL is the only stateful
component and runs as a StatefulSet with a persistent volume.

### 4.2 Data model
Two tables, `users` and `tasks` (one-to-many, cascade delete), with indexes on owner, status,
priority and due date. Enumerations are stored as `VARCHAR + CHECK` constraints to keep
migrations simple and reversible. The schema is owned exclusively by Alembic migrations.

### 4.3 Security design
STRIDE analysis (`docs/security/threat-model.md`) identified 17 threats across the
application, pipeline and runtime. Key mitigations: bcrypt with timing equalisation; JWT with
pinned algorithm and required claims; the role re-read from the database on each request;
ownership checks returning 404; rate limiting at the application and ingress; security
headers and CSP; non-root, read-only, capability-less containers; default-deny network
policies; and secrets generated at provision time and never stored in Git.

### 4.4 Delivery design
Five GitHub Actions workflows separate concerns: CI (quality and tests), Security
(secrets, SCA, SAST, IaC), CodeQL, IaC validation, and Delivery (build → scan gate → SBOM →
push with provenance → sign/attest → deploy to an ephemeral kind cluster → blue-green switch
→ rollback drill → chaos check → GitOps promotion PR).

### 4.5 Reliability design
- Liveness (`/health/live`, process only) is separated from readiness (`/health/ready`, checks the DB), so a DB outage removes pods from traffic without restart storms.
- HPA on CPU and memory; PDB for voluntary disruptions; resource requests and limits everywhere.
- Migrations run as a one-shot Job with backwards-compatible (expand/contract) changes, so both colours can share the database.
- Backups every 1–6 h (by environment) with checksum, archive validation and a **daily automated restore test**.

---

## 5. Implementation
| Layer | Key artefacts |
|---|---|
| Application | `apps/backend` (≈660 statements), `apps/frontend` (React 19, TypeScript, no UI/chart dependencies) |
| Containers | `docker/*.Dockerfile` (multi-stage, non-root, healthchecks), `docker-compose.yml` (profiles: core / monitoring / loadtest) |
| Kubernetes | `kubernetes/base`, `kubernetes/blue-green`, `kubernetes/overlays/{development,staging,production}` |
| IaC | `terraform/modules/{kind-cluster,platform-addons,app-namespace}`, `terraform/environments/{local,staging,production}` |
| Config management | `ansible/roles/{common,docker,k8s_tools,app_deploy,backup}` |
| Security | `security/` (gitleaks, Trivy, Semgrep rules), `.github/workflows/security.yml`, `codeql.yml` |
| Observability | `observability/` (Prometheus rules, Alertmanager, Loki, Alloy, Grafana dashboards generated by `scripts/generate_observability.py`) |
| Operations | `deployment/scripts`, `deployment/rollback`, `scripts/backup`, `scripts/chaos`, `load-testing/` |

Notable implementation details:
- **Low-cardinality metrics:** the HTTP route label is the *template* (`/api/v1/tasks/{task_id}`), not the concrete URL. An integration test caught a framework-version change that broke this, and the implementation was made framework-independent.
- **Observability-as-code:** one generator produces the Grafana dashboard and the Kubernetes PrometheusRule from the same rule files, and a test fails if they drift.
- **Policy-as-code:** a checker enforces non-root, read-only FS, dropped capabilities, resource limits, probes, PSA labels, default-deny networking, blue-green invariants and "no `:latest` in production". It caught a real misconfiguration during development.
- **Testable deployment scripts:** the blue-green and rollback bash scripts are tested against a stateful fake `kubectl`, which proves the switch, no-switch and auto-rollback branches.

---

## 6. Testing and results
Complete results: `docs/testing/test-results.md`. Summary:

| Test type | Count / measure | Result |
|---|---|---|
| Backend unit | 18 | pass |
| Backend integration (PostgreSQL 16) | 30 | pass |
| Deployment logic and manifest policy | 12 | pass |
| Backend line coverage | 97.9 % | ≥ 85 % gate |
| Frontend unit/page tests | 20 (79.3 % coverage) | pass |
| Browser E2E (Playwright) | 4 | pass |
| Kubernetes schema validation (K8s 1.31, strict) | 36 core objects × 3 overlays | pass |
| Dependency CVEs (pip-audit, npm audit) | — | 0 known |
| SAST (Bandit, custom Semgrep) | — | 0 findings |

### 6.1 Performance
| Scenario | Throughput | Error rate | p95 |
|---|---|---|---|
| Baseline, 25 users | 20.2 req/s | 0.00 % | 24 ms |
| Stress, 100 users — before | 2.7 req/s | 39.56 % | 59,000 ms |
| Stress, 100 users — after fixes | **50.0 req/s** | **0.67 %** | **170 ms** |

Root cause: registration and login held a pooled database connection during ~250 ms of
bcrypt CPU work, which exhausted the 15-connection pool. Fixes: perform hashing outside the
transaction; fail fast (5 s pool timeout → HTTP 503 with `Retry-After`); cap concurrent bcrypt
operations at the CPU count. The residual errors are limited to a deliberate burst of 100
registrations on a 2-vCPU host shared with the load generator. That is an intentional security
cost, addressed operationally by horizontal autoscaling. Full analysis:
`docs/testing/performance-report.md`.

### 6.2 Recovery
A full logical backup (56 KB, 236 users, 1,471 tasks) completed in 0.18 s and restored into a
scratch database in 0.17 s with identical row counts and schema revision. This is well inside
the 30-minute RTO target. RPO is bounded by backup frequency (1 h in production, 6 h in staging).

---

## 7. Discussion
**Blue-green on vanilla Kubernetes** proved simple and robust. A single Service-selector patch
gives atomic cut-over and seconds-fast rollback, and the preview Service enables realistic
pre-release testing without user impact. The main constraint is the shared database, which
the expand/contract migration discipline addresses.

**Measuring rather than assuming** changed the outcome. Without the stress test, the
pool-exhaustion defect would have surfaced as a production incident. The SLO gate in the
Locust file turns performance into a pass/fail criterion consistent with the alerting rules.

**Resource constraints shaped the architecture**: profiles, memory limits, a single-node
kind cluster, opt-in monitoring and dependency-free charts. These are the same disciplines
used for cost control in the cloud.

---

## 8. Limitations
1. Container builds, image scanning, signing and Kubernetes deployment are implemented and wired into CI, but were not executed in the author's build sandbox because of network restrictions. They must be run on the target machine or in GitHub Actions (documented in `test-results.md` §3).
2. A single PostgreSQL instance is a single point of failure. Production would use replication or an operator (CloudNativePG) with point-in-time recovery.
3. No admission-time enforcement of image signatures yet.
4. JWTs cannot be revoked before expiry (mitigated by short TTLs and per-request user checks).
5. Performance numbers come from a small shared host and are conservative, not representative of production hardware.

## 9. Future work
- Admission policies (Kyverno `verifyImages`, Pod Security policies as code in-cluster).
- Canary releases with Argo Rollouts and automated analysis against SLO metrics.
- OpenTelemetry distributed tracing correlated with the existing request IDs.
- PostgreSQL HA with continuous WAL archiving (RPO of minutes).
- OIDC/MFA authentication; refresh-token rotation.
- DORA metrics dashboard computed from GitHub deployment events.

## 10. Conclusion
DevSecOps360 meets its objectives. It delivers a working, secure application through a fully
automated, security-gated pipeline onto a hardened Kubernetes platform with zero-downtime
blue-green releases, explicit reliability objectives, actionable alerting, verified recovery
procedures and reproducible infrastructure. The project demonstrates engineering practices
(measurement, automation, defence in depth and documented trade-offs) that carry over
directly to professional platform and SRE work.

## References
1. B. Beyer, C. Jones, J. Petoff, N. R. Murphy (eds.), *Site Reliability Engineering*, O'Reilly, 2016.
2. B. Beyer et al. (eds.), *The Site Reliability Workbook*, O'Reilly, 2018 (ch. 5, "Alerting on SLOs").
3. N. Forsgren, J. Humble, G. Kim, *Accelerate: The Science of Lean Software and DevOps*, IT Revolution, 2018.
4. NIST SP 800-218, *Secure Software Development Framework (SSDF) v1.1*, 2022.
5. OWASP Foundation, *OWASP Top 10: 2021*.
6. OpenSSF, *Supply-chain Levels for Software Artifacts (SLSA) specification v1.0*.
7. Sigstore project documentation: cosign keyless signing.
8. Kubernetes documentation: Pod Security Standards; Network Policies; Horizontal Pod Autoscaling.
9. J. Humble, D. Farley, *Continuous Delivery*, Addison-Wesley, 2010.
10. M. Nygard, "Documenting Architecture Decisions", 2011.

## Appendices
- A. Architecture diagrams: `docs/architecture/architecture.md`
- B. ADRs: `docs/adr/`
- C. Threat model: `docs/security/threat-model.md`
- D. SLOs and alerting: `docs/sre/slos.md`
- E. Runbooks: `docs/runbooks/`
- F. Test results and evidence: `docs/testing/`, `docs/evidence/`
