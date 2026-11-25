# Database

| Path | Purpose |
|---|---|
| `init/` | One-time PostgreSQL initialisation (extensions, timeouts). Mounted into the `db` container. |
| `schema.md` | Entity-relationship diagram and table reference. |
| `../apps/backend/migrations/` | **Alembic migrations — the source of truth for the schema.** |
| `../apps/backend/app/sample_data.json` | Demo users and tasks loaded by `python -m app.seed --sample-data`. |
| `../scripts/backup/` | Automated `pg_dump` backup, restore and restore-verification scripts. |

## Common commands

```powershell
# Apply migrations (Compose runs this automatically at backend start)
docker compose exec backend alembic upgrade head
# Create a new migration after changing app/models.py
docker compose exec backend alembic revision --autogenerate -m "add tags"
# Roll back one migration
docker compose exec backend alembic downgrade -1
# psql shell
docker compose exec db psql -U devsecops -d devsecops360
```

Note: `pg_stat_statements` needs `shared_preload_libraries=pg_stat_statements`; the
extension is created so it can be enabled later without a schema change.
