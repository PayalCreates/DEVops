# DevSecOps360 — Architecture

## 1. Context

DevSecOps360 is a task-management application **and** the delivery platform around it.
The application is deliberately small. The engineering effort goes into how it is
built, secured, deployed, observed and recovered.

```mermaid
flowchart LR
    dev([Developer]) -- git push / PR --> gh[(GitHub repo)]
    gh --> ci[GitHub Actions<br/>CI · Security · Delivery · IaC]
    ci -- signed images + SBOM --> ghcr[(GHCR registry)]
    ci -- GitOps PR --> gh
    ghcr --> k8s[Kubernetes<br/>kind / any cluster]
    gh -. Argo CD sync .-> k8s
    user([End user]) -- HTTPS --> k8s
    k8s -- metrics/logs --> obs[Prometheus · Grafana · Loki · Alertmanager]
    obs -- alerts --> oncall([On-call])
```

## 2. Application architecture

```mermaid
flowchart LR
    subgraph Browser
      spa[React + Vite SPA<br/>TypeScript]
    end
    subgraph web["frontend (nginx, UID 101)"]
      nginx[Static files<br/>CSP + security headers<br/>reverse proxy /api]
    end
    subgraph api["backend (FastAPI, UID 10001)"]
      mw[Middleware: request-id · JSON logs ·<br/>Prometheus RED metrics · security headers]
      auth[Auth: JWT HS256 · bcrypt · rate limit]
      rbac[RBAC: admin / manager / user]
      routes[Routes: auth · users · tasks · analytics · health]
      orm[SQLAlchemy 2 ORM]
    end
    db[(PostgreSQL 16<br/>Alembic-managed schema)]
    spa -->|same-origin /api/v1| nginx --> mw --> auth --> rbac --> routes --> orm --> db
```

| Concern | Implementation |
|---|---|
| AuthN | `POST /auth/login` → JWT (HS256, `exp`/`iat`/`iss`, 60 min). bcrypt cost 12, timing-equalised for unknown users. |
| AuthZ | `require_roles()` dependency; ownership checks on every task query (404 not 403 to prevent ID probing). |
| Validation | Pydantic schemas (lengths, enums, password policy); uniform 422 error shape. |
| Errors | No stack traces to clients; a 500 includes a `request_id` for log correlation; DB overload returns 503 + `Retry-After`. |
| Observability | `/metrics` (RED + business metrics), JSON logs with `request_id`, `/health/live` and `/health/ready`. |
| Blue-green identity | `APP_COLOR` env → `/api/v1/version` and the `app_info` metric. |

### Data flow: create a task
1. The SPA sends `POST /api/v1/tasks` with `Authorization: Bearer <jwt>`.
2. nginx proxies to the `backend` Service and adds `X-Request-ID`.
3. Middleware starts a timer, binds `request_id` to the logging context and increments in-flight requests.
4. `get_current_user` verifies the JWT signature, expiry and issuer, loads the user and rejects inactive accounts.
5. Pydantic validates the body. The ORM inserts the row inside a transaction.
6. The response carries security headers. Metrics `http_requests_total{route="/api/v1/tasks",status="201"}` and the latency histogram are updated. One JSON log line is emitted, and Alloy ships it to Loki.

## 3. Delivery pipeline

```mermaid
flowchart TB
    pr[Pull request] --> ci
    subgraph ci[ci.yml]
      b[Backend: ruff · bandit · pytest on Postgres · coverage ≥85% · migration round-trip]
      f[Frontend: eslint · tsc · vitest · build]
      e[E2E: compose up → smoke → Playwright]
      b & f --> e
    end
    pr --> sec
    subgraph sec[security.yml + codeql.yml]
      s1[gitleaks]; s2[pip-audit · npm audit · Trivy fs]; s3[Semgrep · CodeQL]; s4[Trivy IaC]; s5[Dependency review]
    end
    pr --> iac[iac.yml: terraform validate · tflint · kustomize+kubeconform · policy check · ansible-lint · promtool]
    merge[Merge to main] --> del
    subgraph del[delivery.yml]
      build[Build image] --> scan[Trivy gate: fixable CRITICAL = fail] --> sbom[SBOM SPDX+CycloneDX] --> push[Push GHCR + SLSA provenance] --> sign[cosign keyless sign + attest SBOM]
      sign --> kind[Ephemeral kind cluster: deploy blue → blue-green switch → rollback drill → chaos kill-pod]
      kind --> gitops[PR: bump staging image tag]
    end
    gitops --> argo[Argo CD syncs staging] --> prod[Manual promotion to production]
```

## 4. Kubernetes architecture

```mermaid
flowchart TB
    subgraph cluster[kind cluster · created by Terraform]
      subgraph traefik[ns traefik]
        tr[Traefik ingress<br/>NodePort 30080 → laptop :8088]
      end
      subgraph app["ns devsecops360-dev · PSA restricted · default-deny NetworkPolicies"]
        ing[Ingress + Middlewares<br/>rate-limit · security headers]
        fe[Deployment frontend]
        svc{{Service backend<br/>selector color=ACTIVE}}
        prev{{Service backend-preview<br/>selector color=IDLE}}
        blue[Deployment backend-blue<br/>HPA · PDB]
        green[Deployment backend-green<br/>HPA · PDB]
        pg[(StatefulSet postgres<br/>PVC 1Gi)]
        job[Job db-migrate]
        cron[CronJobs db-backup · db-restore-verify<br/>PVC db-backups]
      end
      subgraph mon[ns monitoring · optional]
        prom[Prometheus] --- graf[Grafana] --- loki[Loki] --- alloy[Alloy]
      end
    end
    tr --> ing --> fe --> svc
    svc --> blue
    prev -.-> green
    blue & green --> pg
    job --> pg
    cron --> pg
    prom -. PodMonitor scrape .-> blue & green
```

**Security layers in the namespace:** Pod Security Admission `restricted`. Every pod runs
non-root with a read-only root filesystem, all capabilities dropped and seccomp
`RuntimeDefault`. No ServiceAccount tokens are mounted. Default-deny ingress and egress,
with explicit allow rules. LimitRange and ResourceQuota cap usage. RBAC uses namespaced
`deployer` and `viewer` roles only.

## 5. Environments

| | Development | Staging | Production |
|---|---|---|---|
| Where | kind on the laptop | any cluster (Terraform `staging`) | any cluster (Terraform `production`) |
| Images | `:local`, loaded into kind | GHCR `sha-<commit>`, GitOps PR | GHCR semver tag (policy forbids `:latest`) |
| Replicas (backend) | 1 (HPA ≤2) | 2 (HPA 2–4) | 3 (HPA 3–6) |
| Docs (`/docs`) | on | on | **off** |
| Backups | every 2 h | every 6 h | hourly (RPO ≤ 1 h) |
| Deploy | script / Ansible | Argo CD auto-sync | Argo CD manual sync + blue-green |

## 6. Resource budget (8 GB laptop)

| Mode | Components | Measured on | Approx. RAM |
|---|---|---|---|
| Compose core | db + backend + frontend | Compose `mem_limit` caps | ≤ 576 MB (caps) |
| Compose full | core + Prometheus, Grafana, Loki, Alloy, Alertmanager, pg-exporter | caps | ≤ 1.5 GB (caps) |
| kind dev | node + Traefik + metrics-server + app | estimate | ~1.5–2 GB |
| kind + monitoring | above + kube-prometheus-stack + Loki | estimate | ~3–3.5 GB |

Run **either** Compose **or** kind, not both. Monitoring is opt-in in both.
