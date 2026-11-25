# ADR-0006: Kustomize overlays for application manifests

**Status:** Accepted

## Decision
Use plain YAML in `kubernetes/base` + `kubernetes/blue-green`, specialised per environment
by `kubernetes/overlays/{development,staging,production}` using JSON6902 patches. Helm is
used only to install **third-party** add-ons (Traefik, monitoring, Argo CD) via Terraform.

## Why
- Kustomize is built into `kubectl` (`kubectl apply -k`), so there is no extra tool for reviewers.
- Manifests stay valid Kubernetes YAML that kubeconform, Trivy and our policy checker can scan.
- Overlays make environment differences explicit and diff-able. Templated charts hide them.

## Consequences
+ The same manifests run in CI (kind), locally, and under Argo CD.
− No packaging or versioning of the app as a chart, which we don't need for one app.
