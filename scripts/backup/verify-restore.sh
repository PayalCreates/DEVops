#!/usr/bin/env bash
# Non-destructive restore test: restore the latest backup into a scratch database,
# run sanity checks, report timings, drop the scratch database.
# This is how RTO is MEASURED rather than guessed.
set -euo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
set -a; [ -f .env ] && . ./.env; set +a

file="${1:-$(ls -1t backups/devsecops360-*.dump 2>/dev/null | head -n1)}"
[ -n "$file" ] && [ -f "$file" ] || { echo '{"msg":"verify_failed","reason":"no backup found"}'; exit 1; }
( cd "$(dirname "$file")" && sha256sum -c --quiet "$(basename "$file").sha256" )

scratch="restore_verify_$(date +%s)"
psql_db() { docker compose exec -T db psql -U "$POSTGRES_USER" -v ON_ERROR_STOP=1 "$@"; }
cleanup() { psql_db -d postgres -qc "DROP DATABASE IF EXISTS $scratch" >/dev/null || true; }
trap cleanup EXIT

start=$(date +%s)
psql_db -d postgres -qc "CREATE DATABASE $scratch"
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$scratch" --no-owner "/backups/$(basename "$file")"
restore_s=$(( $(date +%s) - start ))

users=$(psql_db -d "$scratch" -tAc "SELECT count(*) FROM users")
tasks=$(psql_db -d "$scratch" -tAc "SELECT count(*) FROM tasks")
rev=$(psql_db -d "$scratch" -tAc "SELECT version_num FROM alembic_version")
orphans=$(psql_db -d "$scratch" -tAc "SELECT count(*) FROM tasks t LEFT JOIN users u ON u.id=t.owner_id WHERE u.id IS NULL")

[ "$users" -ge 1 ] || { echo '{"msg":"verify_failed","reason":"no users in backup"}'; exit 1; }
[ "$orphans" -eq 0 ] || { echo '{"msg":"verify_failed","reason":"orphaned tasks"}'; exit 1; }

backup_age_min=$(( ( $(date +%s) - $(stat -c %Y "$file") ) / 60 ))
echo "{\"msg\":\"restore_verify_ok\",\"file\":\"$file\",\"users\":$users,\"tasks\":$tasks,\"alembic\":\"$rev\",\"restore_seconds\":$restore_s,\"backup_age_minutes\":$backup_age_min}"
