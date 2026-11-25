<#
.SYNOPSIS  Local security scans on Windows (Docker Desktop required). Mirrors security-scan.sh.
#>
$ErrorActionPreference = 'Continue'
Set-Location (Join-Path $PSScriptRoot '..')
New-Item -ItemType Directory -Force reports/security | Out-Null
$trivy = 'aquasec/trivy:0.58.1'
$gitleaks = 'ghcr.io/gitleaks/gitleaks:v8.21.2'
$pwdUnix = (Get-Location).Path
$failed = $false

Write-Host "`n== Secrets (gitleaks) ==" -ForegroundColor Cyan
docker run --rm -v "${pwdUnix}:/repo" $gitleaks detect --source /repo --config /repo/security/gitleaks.toml --redact
if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host "`n== Trivy filesystem (deps, secrets, misconfig) ==" -ForegroundColor Cyan
docker run --rm -v "${pwdUnix}:/src" -w /src $trivy fs --config security/trivy.yaml --exit-code 1 .
if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host "`n== Trivy IaC config ==" -ForegroundColor Cyan
docker run --rm -v "${pwdUnix}:/src" -w /src $trivy config --severity HIGH,CRITICAL --ignorefile security/.trivyignore.yaml --exit-code 1 .
if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host "`n== bandit + pip-audit ==" -ForegroundColor Cyan
Push-Location apps/backend; bandit -r app -c pyproject.toml -ll; if ($LASTEXITCODE -ne 0) { $failed = $true }; Pop-Location
pip-audit -r apps/backend/requirements.txt; if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host "`n== npm audit ==" -ForegroundColor Cyan
Push-Location apps/frontend; npm audit --omit=dev --audit-level=high; if ($LASTEXITCODE -ne 0) { $failed = $true }; Pop-Location

if ($failed) { Write-Host "`nONE OR MORE SECURITY GATES FAILED" -ForegroundColor Red; exit 1 }
Write-Host "`nALL SECURITY GATES PASSED" -ForegroundColor Green
