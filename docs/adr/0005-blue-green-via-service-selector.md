# ADR-0005: Blue-green deployment via Service selector switch

**Status:** Accepted

## Context
Releases must be zero-downtime, validated before users see them, and instantly
reversible. Options: rolling update, blue-green, canary (Argo Rollouts or a service mesh).

## Decision
Two identical backend Deployments, `backend-blue` and `backend-green`, generated from one
template with Kustomize `nameSuffix` and a `devsecops360/color` label in the selector.
- `Service backend` selects the **active** colour. The frontend and ingress only talk to it.
- `Service backend-preview` selects the **idle** colour, for in-cluster pre-release testing.
- The script (`deployment/scripts/blue-green-deploy.*`) runs these steps: migrate, roll the idle colour, smoke test via preview, **patch the selector** (atomic), verify through the public path, and roll back automatically on failure.
- The old colour keeps running, so rollback is a single selector patch measured in seconds.

## Alternatives considered
- **Rolling update:** no pre-release validation; rollback means another rollout.
- **Canary with Argo Rollouts or Istio:** finer-grained, but adds a controller or mesh that costs several hundred MB to GBs of RAM. We document canary as a future enhancement.
- **Switching at the ingress:** couples releases to the ingress implementation. A Service selector works on any cluster.

## Consequences
+ Instant, verifiable cut-over and rollback; works on vanilla Kubernetes.
+ The preview Service enables realistic smoke tests with zero user impact.
− Twice the backend capacity during a release (mitigated by `SCALE_DOWN_OLD=true` on the laptop).
− Both colours share one database, so schema changes **must** be backwards compatible (see ADR-0010).
− In-flight requests on the old colour are not cut (pods keep running), but new connections go to the new colour after kube-proxy updates (≈1–3 s).
