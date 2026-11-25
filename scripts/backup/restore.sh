#!/usr/bin/env bash
# Restore a backup into the running Compose database (DESTRUCTIVE: replaces data).
#   ./scripts/backup/restore.sh backups/devsecops360-20261125T060000Z.dump
#   ./scripts/backup/restore.sh latest
set -euo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
set -a; [ -f .env ] && . ./.env; set +a

file="${1:?usage: restore.sh <backup.dump|latest>}"
if [ "$file" = "latest" ]; then
  file="$(ls -1t backups/devsecops360-*.dump | head -n1)"
fi
[ -f "$file" ] || { echo "backup not found: $file" >&2; exit 1; }
( cd "$(dirname "$file")" && sha256sum -c "$(basename "$file").sha256" )

if [ "${FORCE:-}" != "yes" ]; then
  read -r -p "This REPLACES database '$POSTGRES_DB' with $file. Type 'restore' to continue: " ok
  [ "$ok" = "restore" ] || { echo "aborted"; exit 1; }
fi

start=$(date +%s)
echo '{"msg":"stopping backend to block writes during restore"}'
docker compose stop backend

docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$POSTGRES_DB";
CREATE DATABASE "$POSTGRES_DB" OWNER "$POSTGRES_USER";
SQL
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner \
  "/backups/$(basename "$file")"

docker compose start backend
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT 'users=' || (SELECT count(*) FROM users) || ' tasks=' || (SELECT count(*) FROM tasks)"
echo "{\"msg\":\"restore_ok\",\"file\":\"$file\",\"rto_seconds\":$(( $(date +%s) - start ))}"
