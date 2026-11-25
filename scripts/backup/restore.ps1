<#
.SYNOPSIS  Restore a backup into the running Compose database (DESTRUCTIVE).
.EXAMPLE   .\scripts\backup\restore.ps1 -File latest
.EXAMPLE   .\scripts\backup\restore.ps1 -File backups\devsecops360-20261125T060000Z.dump -Force
#>
param([Parameter(Mandatory)][string]$File, [switch]$Force)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..')
Get-Content .env | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim())
}

if ($File -eq 'latest') {
    $File = (Get-ChildItem backups -Filter 'devsecops360-*.dump' | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}
if (-not (Test-Path $File)) { throw "Backup not found: $File" }
$name = Split-Path $File -Leaf
$expected = (Get-Content "$File.sha256").Split(' ')[0]
$actual = (Get-FileHash $File -Algorithm SHA256).Hash.ToLower()
if ($expected -ne $actual) { throw "Checksum mismatch for $name — refusing to restore" }

if (-not $Force) {
    $ok = Read-Host "This REPLACES database '$($env:POSTGRES_DB)' with $name. Type 'restore' to continue"
    if ($ok -ne 'restore') { Write-Output 'aborted'; exit 1 }
}

$sw = [Diagnostics.Stopwatch]::StartNew()
docker compose stop backend
$sql = @"
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$($env:POSTGRES_DB)' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$($env:POSTGRES_DB)";
CREATE DATABASE "$($env:POSTGRES_DB)" OWNER "$($env:POSTGRES_USER)";
"@
$sql | docker compose exec -T db psql -U $env:POSTGRES_USER -d postgres -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw 'database recreate failed' }
docker compose exec -T db pg_restore -U $env:POSTGRES_USER -d $env:POSTGRES_DB --no-owner "/backups/$name"
if ($LASTEXITCODE -ne 0) { throw 'pg_restore failed' }
docker compose start backend
Write-Output (@{ msg = 'restore_ok'; file = $name; rto_seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1) } | ConvertTo-Json -Compress)
