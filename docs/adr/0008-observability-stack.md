# ADR-0008: Prometheus, Grafana, Loki and Alloy

**Status:** Accepted

## Decision
- **Metrics:** the app exposes Prometheus metrics (RED method plus business counters). Prometheus scrapes them. Recording rules compute SLIs, and multi-window burn-rate alerts go to Alertmanager.
- **Logs:** the app writes structured JSON to stdout. **Grafana Alloy** ships container logs to **Loki** (single-binary, filesystem storage). `level` becomes a label; `request_id` and `route` are structured metadata, which avoids high label cardinality.
- **Dashboards:** generated from code (`scripts/generate_observability.py`), so the Compose and Kubernetes stacks share one dashboard and one set of rules.
- **Promtail is not used:** it reached end-of-life in 2026; Alloy is its supported successor.
- **ELK is not used:** Elasticsearch alone needs roughly 2–4 GB of RAM.

## Consequences
+ One query language family (PromQL/LogQL) in one UI, correlated by `request_id`.
+ Fits in under 1 GB of RAM in Compose.
− No distributed tracing yet. OpenTelemetry is listed as a future enhancement; the request-id propagation is the first step toward it.
