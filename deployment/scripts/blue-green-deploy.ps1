<#
.SYNOPSIS
  Blue-Green deployment of the backend with validation and automatic rollback.
.DESCRIPTION
  Same algorithm as blue-green-deploy.sh — see docs/deployment/blue-green.md.
.EXAMPLE
  .\deployment\scripts\blue-green-deploy.ps1 -Image devsecops360-backend:v1.1.0
.EXAMPLE
  .\deployment\scripts\blue-green-deploy.ps1 -Image devsecops360-backend:v1.1.0 -ScaleDownOld
#>
param(
    [Parameter(Mandatory)][string]$Image,
    [string]$Namespace = 'devsecops360-dev',
    [switch]$ScaleDownOld
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib.ps1')

$sw = [Diagnostics.Stopwatch]::StartNew()
$active = Get-ActiveColor $Namespace
$idle = Get-OtherColor $active
$replicas = [int](kubectl -n $Namespace get deploy "backend-$active" -o jsonpath='{.spec.replicas}')
if ($replicas -lt 1) { $replicas = 1 }
$oldImage = kubectl -n $Namespace get deploy "backend-$active" -o jsonpath='{.spec.template.spec.containers[0].image}'
Write-Step "active=$active ($oldImage) -> deploying $Image to $idle"

# 1. Migrations with the new image
Write-Step 'running database migrations'
kubectl -n $Namespace delete job db-migrate --ignore-not-found --wait=true | Out-Null
(Get-Content "$RepoRoot/kubernetes/base/migrate-job.yaml" -Raw) -replace 'image: devsecops360-backend\r?\n', "image: $Image`n" |
    kubectl -n $Namespace apply -f - | Out-Null
kubectl -n $Namespace wait --for=condition=complete job/db-migrate --timeout=300s | Out-Null
if ($LASTEXITCODE -ne 0) { kubectl -n $Namespace logs job/db-migrate --tail=50; throw 'migration failed - nothing switched' }
Write-Ok 'migrations applied'

# 2. Roll out to the idle colour
kubectl -n $Namespace set image "deploy/backend-$idle" "backend=$Image" | Out-Null
kubectl -n $Namespace scale "deploy/backend-$idle" --replicas=$replicas | Out-Null
kubectl -n $Namespace rollout status "deploy/backend-$idle" --timeout=180s
if ($LASTEXITCODE -ne 0) { throw "backend-$idle not ready - traffic still on $active" }
Write-Ok "backend-$idle ready"

# 3. Pre-switch smoke test via preview service
if (-not (Invoke-Smoke $Namespace 'http://backend-preview:8000' $idle $Image)) {
    throw "pre-switch smoke test failed on $idle - traffic still on $active"
}
Write-Ok 'pre-switch smoke test passed'

# 4. Switch
Write-Step "SWITCHING traffic $active -> $idle"
Switch-Traffic $Namespace $idle

# 5. Post-switch verification with automatic rollback
Start-Sleep 3
if (-not (Invoke-Smoke $Namespace 'http://frontend:8080' $idle $Image)) {
    Write-Step "post-switch verification FAILED - rolling back to $active"
    Switch-Traffic $Namespace $active
    throw "deployment rolled back; $active ($oldImage) is serving"
}
Write-Ok 'post-switch verification passed'

if ($ScaleDownOld) { kubectl -n $Namespace scale "deploy/backend-$active" --replicas=0 | Out-Null }
@{ event = 'blue_green_deploy'; result = 'success'; from = $active; to = $idle; image = $Image; total_seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1) } | ConvertTo-Json -Compress
