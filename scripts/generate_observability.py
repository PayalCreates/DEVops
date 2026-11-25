#!/usr/bin/env python3
"""Observability-as-code generator.

    python scripts/generate_observability.py

1. Builds the Grafana dashboard JSON from the panel definitions below.
2. Writes it for Docker Compose (observability/grafana/dashboards/) and for
   Kubernetes (observability/kubernetes/app-monitoring/, loaded as a ConfigMap).
3. Wraps the Prometheus rule files (observability/prometheus/rules/*.yml) into a
   PrometheusRule CRD so Compose and Kubernetes share ONE set of SLO/alert rules.

Edit this script or the rule files, never the generated outputs.
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "observability/grafana/dashboards"
K8S = ROOT / "observability/kubernetes/app-monitoring"
RULES = ROOT / "observability/prometheus/rules"
PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
EXCL = 'route!~"/health.*|/metrics"'

_id = 0


def pid() -> int:
    global _id
    _id += 1
    return _id


def stat(title, expr, x, y, unit="percentunit", thresholds=None, decimals=2, w=6):
    return {
        "id": pid(), "type": "stat", "title": title, "datasource": PROM,
        "gridPos": {"x": x, "y": y, "w": w, "h": 4},
        "targets": [{"refId": "A", "expr": expr, "datasource": PROM}],
        "fieldConfig": {"defaults": {
            "unit": unit, "decimals": decimals,
            "thresholds": {"mode": "absolute", "steps": thresholds or [
                {"color": "red", "value": None}, {"color": "green", "value": 0.995}]},
        }, "overrides": []},
        "options": {"colorMode": "background", "reduceOptions": {"calcs": ["lastNotNull"]}},
    }


def ts(title, targets, x, y, unit="short", w=12, h=8):
    return {
        "id": pid(), "type": "timeseries", "title": title, "datasource": PROM,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [{"refId": chr(65 + i), "expr": e, "legendFormat": lf, "datasource": PROM}
                    for i, (e, lf) in enumerate(targets)],
        "fieldConfig": {"defaults": {"unit": unit, "custom": {"fillOpacity": 10}},
                        "overrides": []},
        "options": {"legend": {"displayMode": "table", "placement": "bottom",
                               "calcs": ["mean", "max"]}},
    }


def row(title, y):
    return {"id": pid(), "type": "row", "title": title, "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


panels = [
    row("SLOs & error budget", 0),
    stat("Availability (5m)", "sli:availability:ratio_rate5m", 0, 1),
    stat("Latency SLI: % < 300ms (5m)", "sli:latency_good_ratio:rate5m", 6, 1,
         thresholds=[{"color": "red", "value": None}, {"color": "green", "value": 0.95}]),
    stat("p95 latency", "sli:latency_p95:5m", 12, 1, unit="s", decimals=3,
         thresholds=[{"color": "green", "value": None}, {"color": "red", "value": 0.3}]),
    stat("Error budget remaining (30d)", "slo:error_budget_remaining:ratio30d", 18, 1,
         thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 0.25},
                     {"color": "green", "value": 0.5}]),

    row("Traffic (RED)", 5),
    ts("Requests / s by route",
       [(f"sum by (route) (rate(http_requests_total{{{EXCL}}}[1m]))", "{{route}}")], 0, 6, "reqps"),
    ts("Errors / s by status",
       [(f'sum by (status) (rate(http_requests_total{{{EXCL},status=~"4..|5.."}}[1m]))',
         "{{status}}")], 12, 6, "reqps"),
    ts("Latency percentiles", [
        (f"histogram_quantile({q}, sum by (le) (rate(http_request_duration_seconds_bucket{{{EXCL}}}[5m])))",
         f"p{int(q * 100)}") for q in (0.5, 0.95, 0.99)], 0, 14, "s"),
    ts("p95 latency by route", [
        (f"histogram_quantile(0.95, sum by (le, route) (rate(http_request_duration_seconds_bucket{{{EXCL}}}[5m])))",
         "{{route}}")], 12, 14, "s"),

    row("Deployment & business", 22),
    ts("Serving instances by colour (blue/green)",
       [("count by (color, version) (app_info)", "{{color}} v{{version}}")], 0, 23, w=8),
    ts("In-flight requests", [("sum(http_requests_in_progress)", "in-flight")], 8, 23, w=8),
    ts("Logins by result", [("sum by (result) (rate(auth_login_attempts_total[5m]))",
                             "{{result}}")], 16, 23, "reqps", w=8),
    ts("Tasks created / min", [("sum(rate(tasks_created_total[5m])) * 60", "tasks/min")],
       0, 31, w=8),
    ts("PostgreSQL connections", [("sum(pg_stat_database_numbackends)", "connections")],
       8, 31, w=8),
    ts("PostgreSQL up", [("pg_up", "pg_up")], 16, 31, w=8),

    row("Logs (Loki)", 39),
    {
        "id": pid(), "type": "logs", "title": "Backend warnings & errors", "datasource": LOKI,
        "gridPos": {"x": 0, "y": 40, "w": 24, "h": 10},
        "targets": [{"refId": "A", "datasource": LOKI,
                     "expr": '{service="backend", level=~"WARNING|ERROR|CRITICAL"}'}],
        "options": {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending"},
    },
]

dashboard = {
    "uid": "devsecops360-overview",
    "title": "DevSecOps360 — Service Overview & SLOs",
    "tags": ["devsecops360", "slo", "red"],
    "timezone": "browser",
    "schemaVersion": 39,
    "version": 1,
    "refresh": "10s",
    "time": {"from": "now-1h", "to": "now"},
    "panels": panels,
    "templating": {"list": []},
    "annotations": {"list": []},
}

def prometheus_rule() -> dict:
    groups = []
    for f in sorted(RULES.glob("*.yml")):
        groups.extend(yaml.safe_load(f.read_text(encoding="utf-8"))["groups"])
    return {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "PrometheusRule",
        "metadata": {"name": "devsecops360", "labels": {"release": "monitoring"}},
        "spec": {"groups": groups},
    }


if __name__ == "__main__":
    body = json.dumps(dashboard, indent=2) + "\n"
    for d in (OUT, K8S):
        d.mkdir(parents=True, exist_ok=True)
        (d / "devsecops360-overview.json").write_text(body, encoding="utf-8")
    header = "# GENERATED by scripts/generate_observability.py from observability/prometheus/rules/ — do not edit\n"
    (K8S / "prometheusrule.yaml").write_text(
        header + yaml.safe_dump(prometheus_rule(), sort_keys=False, width=120), encoding="utf-8")
    print(f"dashboard: {len(panels)} panels -> {OUT} and {K8S}")
    print(f"prometheusrule: {sum(len(g['rules']) for g in prometheus_rule()['spec']['groups'])} rules")
