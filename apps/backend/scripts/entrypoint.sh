#!/bin/sh
# Container entrypoint: wait for DB, run migrations, seed admin, start API.
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo '{"msg":"waiting for database"}'
  python - <<'PY'
import time, sys
from sqlalchemy import create_engine, text
from app.core.config import get_settings
url = get_settings().database_url
for attempt in range(30):
    try:
        with create_engine(url).connect() as c:
            c.execute(text("SELECT 1"))
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print(f'{{"msg":"db not ready","attempt":{attempt}}}', flush=True)
        time.sleep(2)
sys.exit("database never became ready")
PY
  alembic upgrade head
  if [ "${SEED_SAMPLE_DATA:-false}" = "true" ]; then
    python -m app.seed --sample-data
  else
    python -m app.seed
  fi
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" --proxy-headers --forwarded-allow-ips='*' --no-server-header
