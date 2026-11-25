<#
.SYNOPSIS  Create the backend-secrets Secret with random values (if not using Terraform).
.EXAMPLE   .\deployment\scripts\create-secrets.ps1 -Namespace devsecops360-dev
#>
param([string]$Namespace = 'devsecops360-dev', [string]$Overlay = 'development', [switch]$Rotate)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib.ps1')

function New-Secret([int]$Bytes) {
    $b = [byte[]]::new($Bytes); [Security.Cryptography.RandomNumberGenerator]::Fill($b)
    return ([Convert]::ToHexString($b)).ToLower()
}

kubectl get ns $Namespace 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { kubectl apply -f "$RepoRoot/kubernetes/overlays/$Overlay/namespace.yaml" | Out-Null }

kubectl -n $Namespace get secret backend-secrets 2>$null | Out-Null
if ($LASTEXITCODE -eq 0 -and -not $Rotate) { Write-Ok "backend-secrets already exists (use -Rotate to replace)"; return }

$admin = "Adm-$(New-Secret 8)"
kubectl -n $Namespace create secret generic backend-secrets `
    --from-literal=POSTGRES_PASSWORD=$(New-Secret 24) `
    --from-literal=JWT_SECRET_KEY=$(New-Secret 32) `
    --from-literal=ADMIN_PASSWORD=$admin `
    --from-literal=DEMO_USER_PASSWORD="Demo-$(New-Secret 6)" `
    --dry-run=client -o yaml | kubectl -n $Namespace apply -f - | Out-Null
Write-Ok "backend-secrets created in $Namespace"
Write-Host "Admin login: admin@devsecops360.dev / $admin  (shown once - store it in your password manager)"
