# Runbook: Bad release → rollback

## Automatic protection
`blue-green-deploy.sh` will **not** switch traffic if the new colour fails its rollout or
the pre-switch smoke test. If the post-switch verification fails, it **switches back
automatically**.

## Manual rollback (after a switch)
```powershell
.\deployment\rollback\rollback.ps1 -Namespace devsecops360-dev
```
```bash
NAMESPACE=devsecops360-dev ./deployment/rollback/rollback.sh
```
What it does: finds the inactive colour, scales it up if needed, patches the `backend`
Service selector back to it, and verifies through the frontend.
Typical time: a few seconds when the old colour is still running; ~20–40 s if it was scaled to 0.

## Manual commands (if scripts are unavailable)
```bash
kubectl -n devsecops360-dev patch svc backend --type merge -p '{"spec":{"selector":{"devsecops360/color":"blue"}}}'
kubectl -n devsecops360-dev rollout undo deploy/backend-green     # revert the idle colour's image too
```

## Compose
`docker compose up -d backend` with the previous `IMAGE_TAG` in `.env`.

## After rollback
- Keep the bad colour running (scaled down) for debugging; check its logs in Loki with `{color="<bad>"}`.
- Write a postmortem if users were affected.
- Database: migrations are backwards compatible (ADR-0010), so **no schema downgrade is needed**.
