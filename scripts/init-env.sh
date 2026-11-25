#!/usr/bin/env bash
# Create .env from .env.example with strong random secrets (idempotent).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { echo ".env already exists — leaving it untouched"; exit 0; }
cp .env.example .env
rand() { openssl rand -hex "$1"; }
sed -i \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(rand 16)|" \
  -e "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$(rand 32)|" \
  -e "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=Admin-$(rand 6)|" \
  -e "s|^DEMO_USER_PASSWORD=.*|DEMO_USER_PASSWORD=Demo-$(rand 4)|" \
  -e "s|^GRAFANA_ADMIN_PASSWORD=.*|GRAFANA_ADMIN_PASSWORD=$(rand 12)|" .env
chmod 600 .env
echo "Created .env. Logins:"
grep -E '^(ADMIN_EMAIL|ADMIN_PASSWORD|DEMO_USER_PASSWORD|GRAFANA_ADMIN_PASSWORD)=' .env
