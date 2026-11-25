<#
.SYNOPSIS
  Windows task runner for DevSecOps360 (PowerShell 7). Mirrors the Makefile.
.EXAMPLE
  .\scripts\dev.ps1 up          # core app, ~600 MB RAM
  .\scripts\dev.ps1 up-full     # + monitoring, ~1.3 GB
  .\scripts\dev.ps1 test
  .\scripts\dev.ps1 down
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'env', 'up', 'up-full', 'down', 'nuke', 'logs', 'ps', 'test', 'lint', 'smoke',
                 'e2e', 'load', 'scan', 'backup', 'restore-verify', 'cluster', 'k8s-deploy', 'status', 'rollback',
                 'cluster-destroy')]
    [string]$Task = 'help',
    [string]$Namespace = 'devsecops360-dev'
)
$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

function Assert-Ok($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }

function New-Hex([int]$n) {
    $b = [byte[]]::new($n); [Security.Cryptography.RandomNumberGenerator]::Fill($b)
    ([Convert]::ToHexString($b)).ToLower()
}

function Initialize-Env {
    if (Test-Path .env) { Write-Host '.env exists - leaving it untouched'; return }
    $c = Get-Content .env.example -Raw
    $c = $c -replace '(?m)^POSTGRES_PASSWORD=.*$', "POSTGRES_PASSWORD=$(New-Hex 16)"
    $c = $c -replace '(?m)^JWT_SECRET_KEY=.*$', "JWT_SECRET_KEY=$(New-Hex 32)"
    $c = $c -replace '(?m)^ADMIN_PASSWORD=.*$', "ADMIN_PASSWORD=Admin-$(New-Hex 6)"
    $c = $c -replace '(?m)^DEMO_USER_PASSWORD=.*$', "DEMO_USER_PASSWORD=Demo-$(New-Hex 4)"
    $c = $c -replace '(?m)^GRAFANA_ADMIN_PASSWORD=.*$', "GRAFANA_ADMIN_PASSWORD=$(New-Hex 12)"
    Set-Content .env $c -Encoding utf8NoBOM -NoNewline
    Write-Host 'Created .env with random secrets. Logins:' -ForegroundColor Green
    Select-String -Path .env -Pattern '^(ADMIN_EMAIL|ADMIN_PASSWORD|DEMO_USER_PASSWORD|GRAFANA_ADMIN_PASSWORD)=' | ForEach-Object { $_.Line }
}

switch ($Task) {
    'help' { Get-Help $PSCommandPath -Detailed | Select-Object -ExpandProperty Examples; break }
    'env' { Initialize-Env }
    'up' { Initialize-Env; docker compose up -d --build --wait; Assert-Ok 'compose up'; Write-Host 'App: http://localhost:8080   API docs: http://localhost:8080/docs' -ForegroundColor Green }
    'up-full' { Initialize-Env; docker compose --profile monitoring up -d --build --wait; Assert-Ok 'compose up'; Write-Host 'App :8080  Grafana :3000  Prometheus :9090  Alertmanager :9093' -ForegroundColor Green }
    'down' { docker compose --profile monitoring --profile loadtest down }
    'nuke' { docker compose --profile monitoring --profile loadtest down -v }
    'logs' { docker compose logs -f backend }
    'ps' { docker compose ps; docker stats --no-stream }
    'test' {
        python -m pytest; Assert-Ok 'pytest'
        Push-Location apps/frontend; npm test; Pop-Location; Assert-Ok 'npm test'
    }
    'lint' {
        Push-Location apps/backend; ruff check .; Assert-Ok 'ruff'; bandit -q -r app -c pyproject.toml; Assert-Ok 'bandit'; Pop-Location
        Push-Location apps/frontend; npm run lint; Assert-Ok 'eslint'; npm run typecheck; Assert-Ok 'tsc'; Pop-Location
    }
    'smoke' { $env:SMOKE_BASE_URL = 'http://localhost:8080'; python -m pytest tests/smoke -v }
    'e2e' { Push-Location tests/e2e; npm ci; npx playwright install chromium; npx playwright test; Pop-Location }
    'load' { locust -f load-testing/locustfile.py --host http://localhost:8080 --headless -u 25 -r 5 -t 3m --csv load-testing/results/baseline --html load-testing/results/baseline.html }
    'scan' { & "$PSScriptRoot/security-scan.ps1" }
    'backup' { & "$PSScriptRoot/backup/backup.ps1" }
    'restore-verify' { wsl bash scripts/backup/verify-restore.sh }
    'cluster' { Push-Location terraform/environments/local; terraform init -input=false; terraform apply; Pop-Location }
    'k8s-deploy' { & "$Root/deployment/scripts/deploy-k8s.ps1" -Namespace $Namespace }
    'status' { kubectl -n $Namespace get deploy,svc -l app.kubernetes.io/name=backend -o wide }
    'rollback' { & "$Root/deployment/rollback/rollback.ps1" -Namespace $Namespace }
    'cluster-destroy' { Push-Location terraform/environments/local; terraform destroy; Pop-Location }
}
