<#
.SYNOPSIS  Instant blue-green rollback (Windows PowerShell 7).
.EXAMPLE   .\deployment\rollback\rollback.ps1 -Namespace devsecops360-dev
#>
param([string]$Namespace = 'devsecops360-dev')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\scripts\lib.ps1')

$sw = [Diagnostics.Stopwatch]::StartNew()
$current = Get-ActiveColor $Namespace
$target = Get-OtherColor $current
Write-Step "rollback requested: $current -> $target ($Namespace)"

$ready = [int](kubectl -n $Namespace get deploy "backend-$target" -o jsonpath='{.status.readyReplicas}')
if ($ready -lt 1) {
    $replicas = kubectl -n $Namespace get deploy "backend-$current" -o jsonpath='{.spec.replicas}'
    Write-Step "backend-$target has no ready pods - scaling to $replicas"
    kubectl -n $Namespace scale "deploy/backend-$target" --replicas=$replicas | Out-Null
    kubectl -n $Namespace rollout status "deploy/backend-$target" --timeout=180s
    if ($LASTEXITCODE -ne 0) { throw 'previous colour failed to start' }
}

$image = kubectl -n $Namespace get deploy "backend-$target" -o jsonpath='{.spec.template.spec.containers[0].image}'
Switch-Traffic $Namespace $target
Write-Ok "traffic switched to $target ($image)"
Start-Sleep 3
if (-not (Invoke-Smoke $Namespace 'http://frontend:8080' $target $image)) { throw 'rollback verification failed' }
@{ event = 'rollback'; result = 'success'; from = $current; to = $target; image = $image; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1) } | ConvertTo-Json -Compress
