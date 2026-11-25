# Backup, restore & disaster recovery

## Objectives
| Environment | Backup frequency | **RPO** (max data loss) | **RTO** (max time to restore) |
|---|---|---|---|
| Development | every 2 h (CronJob) / every 6 h (Ansible cron, Compose) | 2 h / 6 h | 30 min |
| Staging | every 6 h | 6 h | 30 min |
| Production | hourly | **1 h** | **30 min** |

RTO budget for production: detect (5 min) + decide (5 min) + restore (a measured restore of the
sample dataset takes seconds; budget 10 min for realistic sizes) + verify (5 min) + buffer.
Measure your own with `verify-restore.sh`. It prints `restore_seconds`.

**What reduces RPO further:** continuous WAL archiving / PITR (pgBackRest or the
CloudNativePG operator) gives an RPO of minutes. That is documented as the production upgrade path.

## What is backed up
`pg_dump --format=custom` of the application database: schema, data and the `alembic_version`
row. Each dump has a `.sha256` checksum and is validated with `pg_restore --list` **before** it
is published under its final name, so a half-written file can never look like a good backup.

**3-2-1 rule (production):** copy the dumps from the `db-backups` PVC / `./backups` to object
storage in another location (e.g. `rclone` to S3 with object lock). Not automated locally.

## Automated verification
| Where | How |
|---|---|
| Kubernetes | `CronJob db-restore-verify` (daily): restores the newest dump into a scratch DB, checks row counts and the Alembic revision, drops it. JSON result in the job log. |
| Compose | `scripts/backup/verify-restore.sh` (scheduled daily by the Ansible `backup` role) |

## Procedures
### Compose (laptop)
```powershell
.\scripts\backup\backup.ps1                         # take a backup now
.\scripts\backup\restore.ps1 -File latest           # DESTRUCTIVE: replace the DB with the newest backup
```
```bash
./scripts/backup/backup.sh
./scripts/backup/verify-restore.sh                  # non-destructive test restore + timings
FORCE=yes ./scripts/backup/restore.sh latest        # destructive restore
```

### Kubernetes
```bash
NS=devsecops360-dev
kubectl -n $NS create job --from=cronjob/db-backup manual-backup-$(date +%s)        # backup now
kubectl -n $NS create job --from=cronjob/db-restore-verify verify-$(date +%s)       # prove it restores
kubectl -n $NS logs job/verify-<id>                                                 # {"msg":"restore_verify_ok",...}
```
**Full restore (disaster):**
1. Stop writes: `kubectl -n $NS scale deploy/backend-blue deploy/backend-green --replicas=0`
2. Start a helper pod that mounts `db-backups` (reuse the restore-verify CronJob spec) and run:
   `psql -c "DROP DATABASE devsecops360"`, `psql -c "CREATE DATABASE devsecops360"`, then
   `pg_restore -d devsecops360 --no-owner /backups/<file>.dump`
3. Scale the active colour back up; run smoke tests.
4. Record the actual RTO in the incident timeline.

### Total cluster loss
1. `terraform apply` in `terraform/environments/local` recreates the cluster, add-ons, namespace and secrets (~5 min).
2. `deployment/scripts/deploy-k8s.*` deploys the app (~3 min).
3. Restore the newest off-cluster dump as above.
This is why everything is code: the cluster is **cattle**, the backups are the only pets.

## DR drill (quarterly, and for the viva demo)
1. Note the task count. 2. Take a backup. 3. Delete data (`DELETE FROM tasks;`).
4. Restore. 5. Confirm the count matches. 6. Record the timings in `docs/evidence/`.
