# ADR-0011: Design for an 8 GB Windows laptop

**Status:** Accepted

## Decision
- Compose **profiles**: core (3 containers) by default; `monitoring` and `loadtest` are opt-in.
- Memory **limits** on every container (Compose `deploy.resources.limits`; K8s requests and limits plus LimitRange and ResourceQuota).
- WSL2 capped at 4 GB via `.wslconfig`.
- One uvicorn worker per container. Scale with replicas, which keeps memory predictable and metrics per pod.
- kind with a single node. Heavy add-ons (kube-prometheus-stack, Argo CD) are Terraform toggles, off by default.
- The idle blue-green colour can be scaled to zero (`SCALE_DOWN_OLD=true`).
- Hand-written SVG charts instead of a chart library; Alpine and slim base images.

## Consequences
+ The full core platform runs alongside an IDE and a browser.
− The monitoring and Kubernetes demos are run one at a time rather than all together.
