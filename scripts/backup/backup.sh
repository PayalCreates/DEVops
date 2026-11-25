#!/usr/bin/env bash
# PostgreSQL backup for the Docker Compose stack.
#   ./scripts/backup/backup.sh            # writes backups/devsecops360-<UTC>.dump
#   RETENTION_DAYS=7 ./scripts/backup/backup.sh
# Uses pg_dump's custom format (compressed, supports selective/parallel restore).
set -euo pipefail

cd "$(dirname "$0")/../.."
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
mkdir -p "$BACKUP_DIR"

# shellcheck disable=SC1091
set -a; [ -f .env ] && . ./.env; set +a
: "${POSTGRES_USER:?POSTGRES_USER not set (.env missing?)}"
: "${POSTGRES_DB:?POSTGRES_DB not set}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
name="devsecops360-${ts}.dump"
start=$(date +%s)

# Dump inside the db container to /backups (bind-mounted to ./backups)
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --format=custom --compress=6 --no-owner --file="/backups/${name}.partial"

# Verify the archive is readable BEFORE publishing it under its final name
docker compose exec -T db pg_restore --list "/backups/${name}.partial" > /dev/null
mv "$BACKUP_DIR/${name}.partial" "$BACKUP_DIR/${name}"
( cd "$BACKUP_DIR" && sha256sum "$name" > "${name}.sha256" )

bytes=$(stat -c %s "$BACKUP_DIR/$name")
echo "{\"msg\":\"backup_ok\",\"file\":\"$BACKUP_DIR/$name\",\"bytes\":$bytes,\"seconds\":$(( $(date +%s) - start ))}"

# Retention
find "$BACKUP_DIR" -name 'devsecops360-*.dump*' -mtime +"$RETENTION_DAYS" -print -delete \
  | sed 's/^/{"msg":"pruned","file":"/; s/$/"}/'
