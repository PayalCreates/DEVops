# Runbook: Security incident

## A. Brute-force / credential stuffing (`LoginBruteForceSuspected`)
1. Loki: `{service="backend"} |= "login_failed" | json | line_format "{{.client}}"`, then count by client IP.
2. If a few IPs: block at the ingress (a Traefik `ipAllowList`/deny middleware) or upstream firewall.
3. If distributed: lower the rate limit, add CAPTCHA/MFA (roadmap), notify affected users.
4. Check for successful logins from the same IPs (`login_success`). If any, treat the accounts as compromised: deactivate (`PATCH /users/{id}/active?active=false`) and force a reset.

## B. Leaked secret (gitleaks alert, accidental commit, laptop loss)
1. **Rotate first.** Removing a secret from history does not un-leak it.
   - JWT key: `ROTATE=true ./deployment/scripts/create-secrets.sh`, then restart both colours. All sessions are invalidated.
   - DB password: `ALTER USER devsecops PASSWORD '...'`, update the Secret, restart pods.
   - Registry or CI tokens: revoke in GitHub settings.
2. Remove it from Git history (`git filter-repo`) and force-push; invalidate forks and caches.
3. Review access logs for use of the leaked credential during the exposure window.

## C. Critical CVE in a running image
1. `trivy image <deployed image>`: is the vulnerable package actually used and reachable?
2. Patch: bump the base image or dependency. The pipeline rebuilds, scans, signs, then blue-green deploys.
3. If it can't be patched yet, add a scoped and **expiring** entry to `security/.trivyignore.yaml` with a justification, plus compensating controls (NetworkPolicy, WAF rule).

## D. Suspected container compromise
1. **Isolate, don't delete:** label the pod out of the Service (`kubectl label pod <p> app.kubernetes.io/name-`) so it stops receiving traffic but keeps its evidence. The NetworkPolicy still blocks egress to anything but the DB.
2. Capture: `kubectl logs`, `kubectl describe`, `kubectl get pod -o yaml`.
3. Redeploy from a known-good signed image (blue-green), rotate secrets the pod could read, then investigate.
