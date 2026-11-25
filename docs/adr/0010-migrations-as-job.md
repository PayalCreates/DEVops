# ADR-0010: Database migrations as a one-shot Job (expand/contract)

**Status:** Accepted

## Context
With several replicas and two colours, running `alembic upgrade` on every container start
races and couples a pod's readiness to schema changes.

## Decision
- Kubernetes: migrations run once per release in the `db-migrate` Job (an Argo CD `PreSync` hook, or launched by the blue-green script) **before** the new colour starts. Pods have `RUN_MIGRATIONS=false`.
- Compose (single replica): the entrypoint waits for the DB and runs migrations. This is acceptable for one instance.
- **Every migration must be backwards compatible** with the currently live release (expand → migrate → contract):
  1. *Expand*: add nullable columns or new tables; never rename or drop in the same release.
  2. Deploy the code that writes both old and new shapes.
  3. *Contract*: drop the old columns in a later release once no live colour uses them.
- CI runs an upgrade → downgrade → upgrade round-trip against real PostgreSQL.

## Consequences
+ Blue and green can share one database safely, and rollback never needs a schema downgrade.
− Breaking schema changes take two releases.
