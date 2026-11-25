# Shared helpers for the PowerShell deployment scripts (PowerShell 7+).
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

function Write-Step([string]$m) { Write-Host "[$(Get-Date -Format HH:mm:ss)] $m" -ForegroundColor Cyan }
function Write-Ok([string]$m) { Write-Host "[$(Get-Date -Format HH:mm:ss)] OK $m" -ForegroundColor Green }

function Get-ActiveColor([string]$Namespace) {
    $c = kubectl -n $Namespace get svc backend -o jsonpath='{.spec.selector.devsecops360/color}'
    if (-not $c) { throw "cannot read active colour from svc/backend in $Namespace" }
    return $c
}

function Get-OtherColor([string]$Color) { if ($Color -eq 'blue') { 'green' } else { 'blue' } }

function Switch-Traffic([string]$Namespace, [string]$To) {
    $from = Get-OtherColor $To
    $now = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $active = @{ metadata = @{ annotations = @{ 'devsecops360/active-color' = $To; 'devsecops360/switched-at' = $now } }
                 spec = @{ selector = @{ 'devsecops360/color' = $To } } } | ConvertTo-Json -Depth 5 -Compress
    $preview = @{ spec = @{ selector = @{ 'devsecops360/color' = $from } } } | ConvertTo-Json -Depth 5 -Compress
    kubectl -n $Namespace patch svc backend --type merge -p $active | Out-Null
    kubectl -n $Namespace patch svc backend-preview --type merge -p $preview | Out-Null
}

function Invoke-Smoke([string]$Namespace, [string]$Base, [string]$Color, [string]$Image) {
    $name = "smoke-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
    kubectl -n $Namespace create configmap smoke-check --from-file="$PSScriptRoot/smoke_check.py" --dry-run=client -o yaml |
        kubectl -n $Namespace apply -f - | Out-Null
    @"
apiVersion: v1
kind: Pod
metadata:
  name: $name
  labels: { devsecops360/role: smoke-test }
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: smoke
      image: $Image
      imagePullPolicy: IfNotPresent
      command: ["python", "/smoke/smoke_check.py", "$Base", "$Color"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: { drop: ["ALL"] }
      resources:
        requests: { cpu: 10m, memory: 32Mi }
        limits: { cpu: 200m, memory: 96Mi }
      volumeMounts: [{ name: smoke, mountPath: /smoke }]
  volumes:
    - name: smoke
      configMap: { name: smoke-check }
"@ | kubectl -n $Namespace apply -f - | Out-Null
    $phase = ''
    foreach ($i in 1..60) {
        $phase = kubectl -n $Namespace get pod $name -o jsonpath='{.status.phase}' 2>$null
        if ($phase -in 'Succeeded', 'Failed') { break }
        Start-Sleep 2
    }
    kubectl -n $Namespace logs $name
    kubectl -n $Namespace delete pod $name --wait=false 2>$null | Out-Null
    return ($phase -eq 'Succeeded')
}
