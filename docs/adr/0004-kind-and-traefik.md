# ADR-0004: kind for local Kubernetes, Traefik for ingress

**Status:** Accepted

## Context
Kubernetes must run on a Windows laptop with 8 GB RAM, and CI must test the *same*
manifests. Candidates were Minikube, k3d (k3s) and kind.

## Decision
- **kind**, provisioned by Terraform (`tehcyx/kind` provider), single node by default.
- **Traefik** (Helm) as the ingress controller, exposed via NodePort 30080 → `localhost:8088`.
- `*.localtest.me` hostnames (public DNS → 127.0.0.1), so no hosts-file edits are needed.

## Why
| | kind | k3d | Minikube |
|---|---|---|---|
| Same tool in CI | ✅ `helm/kind-action` | possible | awkward |
| Terraform provider | ✅ mature | community | community |
| RAM (1 node) | ~600–900 MB | ~500 MB | ~2 GB (VM driver) |
| NetworkPolicy | ✅ kindnet ≥ v0.24 | ✅ | addon-dependent |

**Why Traefik and not ingress-nginx?** The Kubernetes project retired ingress-nginx in
2026, so new platforms should not adopt it. Traefik is actively maintained, supports
standard `Ingress` resources and gives us rate-limit and header middlewares as CRDs.

## Consequences
+ The CI deploy job runs exactly the manifests and scripts a developer runs locally.
− kind lacks metrics-server and an ingress controller by default. Terraform installs both.
− k3d users can still use the overlays: k3s ships Traefik, so only the NodePort mapping differs.
