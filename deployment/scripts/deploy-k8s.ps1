<#
.SYNOPSIS  Build images, load into kind, apply the Kustomize overlay, wait for readiness.
.EXAMPLE   .\deployment\scripts\deploy-k8s.ps1
.EXAMPLE   .\deployment\scripts\deploy-k8s.ps1 -Tag v1.1.0 -SkipBuild
#>
param(
    [string]$Cluster = 'devsecops360',
    [string]$Overlay = 'development',
    [string]$Namespace = 'devsecops360-dev',
    [string]$Tag = 'local',
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib.ps1')
Set-Location $RepoRoot

if (-not ((kind get clusters) -contains $Cluster)) {
    throw "kind cluster '$Cluster' not found. Run: cd terraform\environments\local; terraform apply"
}
kubectl config use-context "kind-$Cluster" | Out-Null

if (-not $SkipBuild) {
    Write-Step "building images (tag $Tag)"
    docker build -f docker/backend.Dockerfile -t "devsecops360-backend:$Tag" apps/backend
    if ($LASTEXITCODE -ne 0) { throw 'backend build failed' }
    docker build -f docker/frontend.Dockerfile -t "devsecops360-frontend:$Tag" apps/frontend
    if ($LASTEXITCODE -ne 0) { throw 'frontend build failed' }
}
Write-Step 'loading images into kind'
kind load docker-image --name $Cluster "devsecops360-backend:$Tag" "devsecops360-frontend:$Tag"
docker pull -q postgres:16-alpine | Out-Null
kind load docker-image --name $Cluster postgres:16-alpine

& (Join-Path $PSScriptRoot 'create-secrets.ps1') -Namespace $Namespace -Overlay $Overlay

Write-Step "applying overlay $Overlay"
kubectl -n $Namespace delete job db-migrate --ignore-not-found 2>$null | Out-Null  # Jobs are immutable
(kubectl kustomize "kubernetes/overlays/$Overlay") `
    -replace 'image: devsecops360-backend:local', "image: devsecops360-backend:$Tag" `
    -replace 'image: devsecops360-frontend:local', "image: devsecops360-frontend:$Tag" |
    kubectl apply -f -

kubectl -n $Namespace rollout status statefulset/postgres --timeout=300s
kubectl -n $Namespace wait --for=condition=complete job/db-migrate --timeout=300s
kubectl -n $Namespace rollout status "deploy/backend-$(Get-ActiveColor $Namespace)" --timeout=300s
kubectl -n $Namespace rollout status deploy/frontend --timeout=180s
Write-Ok 'deployed. Open http://devsecops360.localtest.me:8088'
kubectl -n $Namespace get pods -o wide
