# 60 viva questions with model answers

Answers are tied to *this* project so you can point at files while answering.

## A. Project & architecture (1–6)
**1. What problem does DevSecOps360 solve?**
It shows how software is delivered safely and repeatably, not only written. Every commit is tested, scanned and signed automatically, then deployed with zero downtime, monitored against SLOs, and recoverable through rollback, backups and self-healing.

**2. Why is the application deliberately simple?**
The grading focus is the delivery platform. A task app still exercises authentication, RBAC, CRUD, analytics and a database, which is enough surface for real testing, security, migrations and performance work.

**3. Describe the request path from browser to database.**
Browser → Traefik ingress (rate limit, headers) → nginx frontend Service (static files, `/api` proxy) → `backend` Service (selects the active colour) → FastAPI pod (middleware: request-id, metrics, logs, headers → JWT auth → RBAC → route) → SQLAlchemy → PostgreSQL.

**4. Why does nginx proxy `/api` instead of the browser calling the API directly?**
A single origin removes CORS complexity, allows a strict CSP (`connect-src 'self'`), hides the backend topology, and lets the frontend follow the active blue-green colour through one Service.

**5. Which parts are stateful and how are they protected?**
Only PostgreSQL: a StatefulSet with a PVC, NetworkPolicy isolation (backend and labelled jobs only, no egress), automated backups with checksums, and a daily automated restore test.

**6. What is an ADR and give one example from the project.**
An Architecture Decision Record captures context, decision and consequences. ADR-0004 chose kind over Minikube/k3d (same tool in CI, Terraform provider, RAM) and Traefik over ingress-nginx (retired in 2026).

## B. Git & CI/CD (7–14)
**7. What branching strategy do you use and why?**
GitHub Flow: `main` is always deployable, work happens on short-lived branches merged via PR with required checks, and Conventional Commits are used. It is simpler than GitFlow and suits continuous delivery.

**8. List the GitHub Actions workflows and what each does.**
`ci.yml` (lint, SAST, tests on Postgres, coverage gate, migration round-trip, frontend build, E2E on Compose), `security.yml` (gitleaks, pip-audit, npm audit, Trivy fs/IaC, Semgrep, dependency review), `codeql.yml`, `iac.yml` (terraform validate/tflint, kustomize+kubeconform, policy check, ansible-lint, promtool), `delivery.yml` (build, scan gate, SBOM, push, sign, deploy-verify on kind, GitOps PR).

**9. What is the difference between continuous delivery and continuous deployment here?**
Staging is continuous deployment (Argo CD auto-syncs after the promotion PR merges). Production is continuous delivery: always releasable, but synced manually after review.

**10. Why does CI run integration tests against PostgreSQL rather than SQLite?**
To catch dialect differences (constraints, types, transaction behaviour) that SQLite hides. Locally SQLite gives speed; CI provides fidelity through a `postgres:16` service container.

**11. What does `concurrency: cancel-in-progress` do?**
It cancels older runs of the same branch when a new commit is pushed, saving runner minutes and giving faster feedback.

**12. Why `permissions: contents: read` at the top of workflows?**
Least privilege for `GITHUB_TOKEN`. Jobs that need more (push packages, OIDC signing, write PRs) request it explicitly.

**13. How do you avoid storing registry credentials in CI?**
The built-in `GITHUB_TOKEN` handles GHCR push, and GitHub OIDC (`id-token: write`) provides keyless cosign signing. There are no long-lived secrets.

**14. What is the coverage gate and current coverage?**
`--cov-fail-under=85`. Current backend coverage is 97.9 % (60 tests on PostgreSQL); frontend is 79.3 %.

## C. Docker (15–20)
**15. Why multi-stage builds?**
Build tools (compilers, npm) stay in the builder stage, and the runtime image contains only the venv or static files. That gives smaller images, a smaller attack surface and fewer CVEs.

**16. How are the containers hardened?**
Non-root fixed UIDs (10001, 101), read-only root FS with tmpfs, `cap_drop: ALL`, `no-new-privileges`, healthchecks, memory/CPU limits, an internal-only data network, and the DB port is not published.

**17. Why does the database network use `internal: true`?**
Containers on it have no route to the internet, so even a compromised DB container can't exfiltrate data or download tools.

**18. Explain the Compose healthcheck and `depends_on: condition: service_healthy`.**
Docker runs the healthcheck command periodically. Dependents start only when the dependency reports healthy (db → backend → frontend), which avoids startup races.

**19. Why one uvicorn worker per container?**
Predictable memory on an 8 GB laptop and correct per-process Prometheus metrics. Scaling happens through more containers or pods (the HPA), not more workers.

**20. What are Compose profiles used for?**
Opt-in groups: the default core (3 services, ~600 MB), `monitoring` (+6 services), `loadtest` (Locust UI). This keeps the laptop responsive.

## D. Kubernetes (21–30)
**21. Difference between liveness, readiness and startup probes in your backend?**
Startup gives the app time to boot. Liveness (`/health/live`, process only) restarts a hung process. Readiness (`/health/ready`, checks the DB) removes the pod from the Service when it can't serve. The DB is deliberately not in liveness, so a DB outage doesn't cause restart storms.

**22. Why is PostgreSQL a StatefulSet and not a Deployment?**
Stable identity (`postgres-0`), stable DNS through a headless Service, and a per-replica PersistentVolumeClaim via `volumeClaimTemplates`.

**23. How do ConfigMaps and Secrets differ, and how are secrets created?**
ConfigMaps hold non-sensitive config. Secrets hold credentials (base64, RBAC-restricted, can be encrypted at rest). The `backend-secrets` Secret is generated by Terraform `random_password` or the create-secrets script and is never committed.

**24. Explain your NetworkPolicies.**
Default deny for all ingress and egress, then allow DNS, Traefik → frontend:8080, frontend → backend:8000, backend/monitoring → backend:8000, backend and labelled jobs → postgres:5432. Postgres has no egress.

**25. What is Pod Security Admission "restricted"?**
A built-in admission controller enforcing the strictest Pod Security Standard: non-root, no privilege escalation, dropped capabilities, seccomp RuntimeDefault, restricted volume types. The namespaces carry `enforce: restricted`.

**26. How does the HPA work and what does it scale on?**
It reads metrics-server CPU and memory every ~15 s and adjusts replicas to keep average CPU near 70 % (memory 80 %), between min and max per environment. Scale-down has a 120 s stabilisation window to avoid flapping.

**27. What is a PodDisruptionBudget for?**
It limits voluntary disruptions (node drains, upgrades) so they never take down more than `maxUnavailable: 1` backend pod at a time.

**28. Why LimitRange and ResourceQuota?**
LimitRange gives default requests and limits to any container that lacks them. ResourceQuota caps total namespace usage. Together they stop one workload from starving the node.

**29. How are migrations run in Kubernetes and why not in the pod entrypoint?**
A one-shot `db-migrate` Job (an Argo CD PreSync hook, or launched by the deploy script) runs before the new colour starts. Running in every pod would race across replicas and colours.

**30. What RBAC exists?**
A namespaced `deployer` Role (patch deployments and services, create jobs and smoke pods, no Secret reads) for the pipeline, a read-only `viewer` Role for developers, and no ServiceAccount tokens mounted in app pods.

## E. Infrastructure as Code & configuration management (31–36)
**31. What does Terraform provision?**
The kind cluster (with port mappings), Helm add-ons (Traefik, metrics-server, and optionally kube-prometheus-stack, Loki, Alloy, Argo CD), the app namespace, and generated secrets, all in one `terraform apply`.

**32. Explain your module structure.**
Three reusable modules (`kind-cluster`, `platform-addons`, `app-namespace`) composed by three environments (`local`, `staging`, `production`) with different inputs. This shows reuse and consistency across environments.

**33. How is Terraform state managed?**
Local state for the single-developer laptop environment (git-ignored, because it contains secrets). Staging and production use an S3-compatible remote backend with encryption and native lockfile locking (`backend.hcl.example`, which works with MinIO locally).

**34. What does idempotency mean in Ansible and how do you show it?**
Running a playbook again changes nothing if the system is already in the desired state. Modules declare state (`apt: state=present`, `cron`, `template`), and tool downloads are skipped when the pinned version is installed. A second run reports `changed=0`.

**35. Why both Terraform and Ansible?**
Terraform manages infrastructure lifecycle (create, destroy, dependency graph, state). Ansible configures machines and runs procedures (toolchain install, Compose deploy, cron backups). They are different tools for different problems.

**36. How are secrets handled in Ansible?**
Ansible Vault-encrypted vars file (git-ignored), passed with `--ask-vault-pass`. Tasks touching secrets use `no_log: true`, and the rendered `.env` is mode 0600.

## F. DevSecOps & supply chain (37–46)
**37. What does "shift left" mean in your pipeline?**
Security checks run as early as possible: pre-commit hooks (gitleaks, ruff), PR checks (SAST, SCA, IaC), and build-time image scanning before push, instead of a security review just before release.

**38. Difference between SAST, SCA and DAST?**
SAST analyses source (Bandit, Semgrep, CodeQL). SCA checks dependencies for known CVEs (pip-audit, npm audit, Trivy). DAST attacks the running app. Our E2E and smoke tests check headers and auth behaviour; OWASP ZAP would be the full DAST step (future work).

**39. What is an SBOM and why generate two formats?**
A Software Bill of Materials lists every component and version in an image. SPDX (an ISO standard, licence-focused) and CycloneDX (security and VEX-focused) cover different consumers. When a new CVE appears, you can query which images contain the package.

**40. How does keyless signing with cosign work?**
In CI, GitHub's OIDC token proves the workflow's identity to Sigstore's Fulcio, which issues a short-lived certificate. cosign signs the image digest, and the signature is recorded in the Rekor transparency log. Verification checks that the certificate identity matches our repo's workflow, with no keys to manage or leak.

**41. What is SLSA provenance?**
A signed attestation describing how an artefact was built (source commit, builder, parameters). `provenance: mode=max` in buildx produces it, which helps prove the image came from our pipeline.

**42. Your Trivy gate fails on "fixable CRITICAL". Why not fail on everything?**
Failing on unfixable or low-severity findings blocks delivery without an actionable fix, which encourages people to bypass the gate. HIGH findings are reported as SARIF and tracked, while CRITICAL findings with a fix available block the release.

**43. Give an example of a custom Semgrep rule and why it exists.**
`fastapi-route-missing-auth` flags any route in the tasks, users or analytics routers without `get_current_user`/`require_roles`. It encodes our authorisation rule so a forgotten dependency fails CI. All 5 custom rules were proven to fire on a vulnerable sample.

**44. How do you prevent IDOR (insecure direct object reference)?**
Every task query filters by `owner_id` unless the user is a manager or admin, and foreign IDs return 404 (not 403) so IDs can't be probed. Integration tests cover read, update and delete across users.

**45. How is password storage secured?**
bcrypt cost 12 with a per-hash salt, a 72-byte limit enforced (not silently truncated), and constant-time-ish login via a dummy-hash comparison for unknown emails. A password policy is enforced on both client and server.

**46. Walk through your threat model method.**
Data-flow diagram with trust boundaries, then STRIDE per element, giving 17 threats with mitigations mapped to code and tests, plus residual risks and a roadmap (signature admission, MFA, External Secrets, Falco).

## G. Blue-green deployment (47–51)
**47. Explain blue-green in your implementation.**
Two Deployments (`backend-blue`, `backend-green`) from one Kustomize template. The `backend` Service selects the active colour and `backend-preview` selects the idle one. A release goes to the idle colour, is smoke-tested through preview, then the selector is patched atomically.

**48. What happens if the new version is broken?**
If the rollout fails, or the pre-switch smoke test fails, traffic never switches. If the post-switch verification through the frontend fails, the script switches back automatically. Six automated tests prove these branches against a fake kubectl.

**49. How fast is rollback and why?**
Seconds: it is one Service-selector patch, because the old colour is still running. If the old colour was scaled to zero to save RAM, rollback first scales it up (~20–40 s).

**50. How do you handle database changes with two live versions?**
Expand/contract migrations: only backwards-compatible changes per release (add nullable columns or tables), so both colours work against the same schema. Destructive changes come in a later release.

**51. Blue-green vs canary vs rolling: when would you pick each?**
Rolling: cheap, no pre-release test. Blue-green: instant rollback and preview testing at the cost of 2× capacity during release. Canary: smallest blast radius with gradual exposure, but needs traffic-splitting tooling (Argo Rollouts or a mesh).

## H. Observability & SRE (52–57)
**52. What are your SLIs and SLOs?**
Availability SLI = non-5xx / all requests, SLO 99.5 %. Latency SLI = share of requests under 300 ms, SLO 95 %. Measured over 30 days, excluding health checks.

**53. What is an error budget and how do you use it?**
1 − SLO = 0.5 % of requests may fail (≈3.6 h of downtime per 30 days). The policy: ship freely above 50 % remaining; require load tests at 25–50 %; feature freeze below 25 %.

**54. Explain multi-window, multi-burn-rate alerting.**
Alert when the error ratio exceeds 14.4× the budget rate over both 1 h and 5 m (fast burn, page), or 6× over 6 h and 30 m (slow burn, ticket). The long window prevents paging on blips, and the short window makes the alert clear quickly after recovery.

**55. What is the RED method and where is it implemented?**
Rate, Errors, Duration per endpoint: the `http_requests_total{route,status}` counter and the `http_request_duration_seconds` histogram in `core/metrics.py`, visualised on the dashboard.

**56. Why do you label metrics with the route template rather than the URL?**
To keep label cardinality bounded. `/tasks/{task_id}` is one series, whereas raw URLs create a series per ID and can take down Prometheus. A test checks this.

**57. How do logs, metrics and requests correlate?**
Each request gets an `X-Request-ID` (propagated from nginx or generated). It appears in every JSON log line, in error responses and in response headers. Alloy keeps it as structured metadata in Loki, so you can jump from a 500 response to its exact log lines.

## I. Testing, performance & resilience (58–60)
**58. Describe the bottleneck you found with load testing.**
At 100 users, auth endpoints held a pooled DB connection during ~250 ms of bcrypt CPU work, which exhausted the pool (15 connections): 30 s waits, 39.6 % HTTP 500s, 2.7 req/s. Fixes: hash outside the transaction, a 5 s pool timeout mapped to 503 + `Retry-After`, and a bcrypt concurrency cap at the CPU count. Result: 0.67 % errors, p95 170 ms, 50 req/s.

**59. What chaos experiments did you design and what do they prove?**
Pod kill (the ReplicaSet replaces it within 60 s), DB outage (readiness 503, zero restarts, auto-recovery through `pool_pre_ping`), CPU spike (HPA scales out), a bad release (blue-green blocks the switch), and Compose SIGKILL (the restart policy recovers). Each has a stated hypothesis and a JSON result.

**60. What are your RPO and RTO and how do you know they're achievable?**
Production RPO ≤ 1 h (hourly backups), RTO ≤ 30 min. Restore is measured, not guessed: the daily `db-restore-verify` job (and `verify-restore.sh`) restores the latest dump into a scratch DB, checks row counts and the schema revision, and reports `restore_seconds`. In testing, a full backup took 0.18 s and the restore 0.17 s with identical row counts.
