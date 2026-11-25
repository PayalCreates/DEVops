<#
.SYNOPSIS  PostgreSQL backup for the Docker Compose stack (Windows PowerShell 7).
.EXAMPLE   .\scripts\backup\backup.ps1
.EXAMPLE   .\scripts\backup\backup.ps1 -RetentionDays 14
#>
param([int]$RetentionDays = 7)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..')

# Load .env into the process environment
Get-Content .env | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim())
}
New-Item -ItemType Directory -Force -Path backups | Out-Null

$ts = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$name = "devsecops360-$ts.dump"
$sw = [Diagnostics.Stopwatch]::StartNew()

docker compose exec -T db pg_dump -U $env:POSTGRES_USER -d $env:POSTGRES_DB `
    --format=custom --compress=6 --no-owner --file="/backups/$name.partial"
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
docker compose exec -T db pg_restore --list "/backups/$name.partial" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "backup archive is not readable" }

Move-Item "backups/$name.partial" "backups/$name"
$hash = (Get-FileHash "backups/$name" -Algorithm SHA256).Hash.ToLower()
"$hash  $name" | Set-Content "backups/$name.sha256" -Encoding ascii -NoNewline

$size = (Get-Item "backups/$name").Length
Write-Output (@{ msg = 'backup_ok'; file = "backups/$name"; bytes = $size; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1) } | ConvertTo-Json -Compress)

Get-ChildItem backups -Filter 'devsecops360-*.dump*' |
    Where-Object LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) |
    ForEach-Object { Remove-Item $_.FullName; Write-Output "{`"msg`":`"pruned`",`"file`":`"$($_.Name)`"}" }
