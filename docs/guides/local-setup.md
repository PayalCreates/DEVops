# Complete local setup

Choose a level. Each one builds on the previous and adds RAM.

| Level | What you get | RAM | Command |
|---|---|---|---|
| **0. Dev mode** | Hot-reload backend + frontend, no Docker | ~300 MB | see §1 |
| **1. Compose core** | db + backend + frontend in hardened containers | ~600 MB | `.\scripts\dev.ps1 up` |
| **2. Compose full** | + Prometheus, Grafana, Loki, Alloy, Alertmanager | ~1.3 GB | `.\scripts\dev.ps1 up-full` |
| **3. Kubernetes** | kind + Traefik + blue-green + NetworkPolicies + CronJobs | ~2 GB | §4 |
| **4. K8s + monitoring** | + kube-prometheus-stack + Loki in cluster | ~3.5 GB | §4 with `enable_monitoring=true` |

> Stop one level before starting another: `.\scripts\dev.ps1 down`, `terraform destroy`.

## 0. Get the code
```powershell
git clone https://github.com/<you>/devsecops360.git C:\dev\devsecops360
Set-Location C:\dev\devsecops360
```
(Not inside OneDrive: sync locks break `node_modules` and `.terraform`.)

## 1. Dev mode (no containers) — fastest feedback loop
```powershell
# Backend (uses SQLite by default; no database install needed)
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r apps/backend/requirements-dev.txt
Set-Location apps/backend
$env:ADMIN_EMAIL='admin@devsecops360.dev'; $env:ADMIN_PASSWORD='Admin-Pass1'; $env:DEMO_USER_PASSWORD='Demo-Pass1'
alembic upgrade head; python -m app.seed --sample-data
uvicorn app.main:app --reload --port 8000             # http://localhost:8000/docs

# Frontend (second terminal) — Vite proxies /api to :8000
Set-Location apps/frontend; npm ci; npm run dev        # http://localhost:5173
```
Run tests: `python -m pytest` (repo root), `npm test` (apps/frontend).

## 2. Docker Compose
```powershell
.\scripts\dev.ps1 up          # creates .env with random secrets on first run, prints logins
docker compose ps             # all "healthy"
```
- App: http://localhost:8080 · API docs: http://localhost:8080/docs
- Logins are printed on first run (also in `.env`): `admin@devsecops360.dev`, and demo users
  `alice@`, `bob@`, `manager@devsecops360.dev` with `DEMO_USER_PASSWORD`.

Full stack with monitoring:
```powershell
.\scripts\dev.ps1 up-full
```
Grafana http://localhost:3000 (admin / `GRAFANA_ADMIN_PASSWORD` from `.env`) → folder
**DevSecOps360** → *Service Overview & SLOs*. Prometheus http://localhost:9090/alerts,
Alertmanager http://localhost:9093. Logs: Grafana → Explore → Loki → `{service="backend"}`.

Smoke and E2E against Compose:
```powershell
.\scripts\dev.ps1 smoke
.\scripts\dev.ps1 e2e
```

## 3. Ansible (optional, inside WSL Ubuntu)
```bash
cd /mnt/c/dev/devsecops360/ansible
ansible-galaxy collection install -r requirements.yml -p ./collections
ansible-playbook playbooks/provision-workstation.yml -K      # toolchain, idempotent
cp inventories/local/group_vars/vault.yml.example inventories/local/group_vars/vault.yml
ansible-vault encrypt inventories/local/group_vars/vault.yml
ansible-playbook playbooks/deploy-compose.yml -e @inventories/local/group_vars/vault.yml --ask-vault-pass
ansible-playbook playbooks/backup.yml                         # cron backups + restore checks
```
Run any playbook twice: the second run should report `changed=0` (idempotency).

## 4. Kubernetes (kind + Terraform)
```powershell
.\scripts\dev.ps1 down                                       # free RAM first
Set-Location terraform\environments\local
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform apply                                              # cluster + Traefik + metrics-server + namespace + secrets
terraform output -raw admin_password                         # admin login
terraform output -raw demo_user_password
Set-Location ..\..\..
.\deployment\scripts\deploy-k8s.ps1                          # build, kind load, apply overlay, wait
```
Open **http://devsecops360.localtest.me:8088**.

Blue-green release:
```powershell
docker build -f docker/backend.Dockerfile -t devsecops360-backend:v1.1.0 apps/backend
kind load docker-image --name devsecops360 devsecops360-backend:v1.1.0
.\deployment\scripts\blue-green-deploy.ps1 -Image devsecops360-backend:v1.1.0
kubectl -n devsecops360-dev get svc backend -o jsonpath='{.spec.selector}'
.\deployment\rollback\rollback.ps1
```
Watch the colour badge in the bottom-left of the UI change between blue and green.

In-cluster monitoring: set `enable_monitoring = true` and `grafana_admin_password` in
`terraform.tfvars`, run `terraform apply`, then:
```powershell
kubectl apply -k observability/kubernetes/app-monitoring
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
```

Tear down: `terraform destroy` (in `terraform/environments/local`).
