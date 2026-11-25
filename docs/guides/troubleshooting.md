# Troubleshooting

## Windows / Docker Desktop
| Symptom | Fix |
|---|---|
| `docker: error during connect … pipe/docker_engine` | Docker Desktop isn't running. Start it and wait for "Engine running". |
| Laptop very slow, `vmmem` uses all RAM | Create `%USERPROFILE%\.wslconfig` with `memory=4GB`, then `wsl --shutdown`. Run only one level (Compose **or** kind). |
| `exec /usr/local/bin/entrypoint.sh: no such file or directory` | CRLF line endings in a shell script. `git config core.autocrlf false`; `git rm --cached -r .; git reset --hard` (`.gitattributes` forces LF). |
| Port 8080 / 3000 already in use | Set `FRONTEND_PORT=8081` in `.env`; find the process: `Get-NetTCPConnection -LocalPort 8080`. |
| `running scripts is disabled on this system` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Files show BOM / YAML parse errors | Use PowerShell 7 (`pwsh`), whose `-Encoding utf8NoBOM` doesn't add a BOM. |

## Compose
| Symptom | Fix |
|---|---|
| `set POSTGRES_PASSWORD in .env` | Run `.\scripts\dev.ps1 env` (creates `.env`). |
| backend `unhealthy`, logs show `db not ready` repeatedly | `docker compose logs db`. A changed `POSTGRES_PASSWORD` after the volume was created needs `docker compose down -v` (deletes data) or `ALTER USER` inside the DB. |
| Frontend 502 on `/api` | The backend is not healthy yet: `docker compose ps`; nginx resolves `backend` at start, so `docker compose restart frontend` after fixing it. |
| Login says "Too many login attempts" | The per-IP+email limit (10/min). Wait 60 s. |
| Grafana has no data | Use `--profile monitoring`; check Prometheus targets at http://localhost:9090/targets. |
| Loki has no logs | Alloy needs `/var/run/docker.sock`; on Docker Desktop enable "Allow the default Docker socket" (Settings → Advanced). |

## Kubernetes (kind)
| Symptom | Fix |
|---|---|
| `ErrImageNeverPull` / `ImagePullBackOff` for `devsecops360-*:local` | `kind load docker-image --name devsecops360 devsecops360-backend:local devsecops360-frontend:local` |
| Pods `CreateContainerConfigError` | The `backend-secrets` Secret is missing: `terraform apply` or `.\deployment\scripts\create-secrets.ps1`. |
| `violates PodSecurity "restricted"` | A pod spec lacks `runAsNonRoot` / `seccompProfile` / dropped caps; copy the securityContext from `kubernetes/blue-green/app/deployment.yaml`. |
| `field is immutable` on `job/db-migrate` | `kubectl -n devsecops360-dev delete job db-migrate`, then re-apply (deploy scripts do this). |
| http://devsecops360.localtest.me:8088 doesn't load | `kubectl -n traefik get pods,svc` (NodePort 30080?); the cluster must be created by Terraform (port mapping). Corporate DNS may block `localtest.me`; add `127.0.0.1 devsecops360.localtest.me` to the hosts file. |
| HPA shows `<unknown>` targets | metrics-server not ready: `kubectl -n kube-system get deploy metrics-server`; `kubectl top pods`. |
| Smoke pod stuck `Pending` | ResourceQuota reached: `kubectl -n devsecops360-dev describe quota`. Scale the idle colour to 0. |
| Traffic doesn't reach backend after the switch | NetworkPolicy: pods need label `app.kubernetes.io/name=backend`; check `kubectl -n <ns> get endpoints backend`. |

## Terraform
| Symptom | Fix |
|---|---|
| `kind_cluster … already exists` | `kind delete cluster --name devsecops360`, or `terraform import`. |
| Helm release timeout | Low RAM. Close apps, keep `enable_monitoring = false`, re-run `terraform apply`. |
| Lost state but the cluster exists | `kind delete cluster --name devsecops360` and apply again (everything is reproducible). |

## Tests
| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: app` | Run pytest from the repo **root** (`tests/conftest.py` adds `apps/backend` to the path). |
| Integration tests against Postgres | `$env:TEST_DATABASE_URL='postgresql+psycopg://user:pass@localhost:5432/testdb'; python -m pytest` |
| Playwright: browser not found | `npx playwright install chromium`, or use installed Chrome: `$env:PW_CHANNEL='chrome'`. |
