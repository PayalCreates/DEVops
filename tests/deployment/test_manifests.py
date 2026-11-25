"""Render every Kustomize overlay and enforce platform policy + blue-green invariants."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/validate/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


render = _load("render_kustomize")
policy = _load("k8s_policy_check")


@pytest.mark.parametrize("overlay", ["development", "staging", "production"])
def test_overlay_renders_and_passes_policy(overlay):
    docs = render.build(ROOT / "kubernetes/overlays" / overlay)
    assert policy.check(docs) == []
    ns = {d["metadata"].get("namespace") for d in docs if d["kind"] != "Namespace"}
    assert len(ns) == 1, f"objects spread across namespaces: {ns}"


def test_production_hardening_differs_from_dev():
    dev = render.build(ROOT / "kubernetes/overlays/development")
    prod = render.build(ROOT / "kubernetes/overlays/production")
    cfg = lambda docs: next(d for d in docs if d["kind"] == "ConfigMap")["data"]  # noqa: E731
    assert cfg(dev)["SEED_SAMPLE_DATA"] == "true" and cfg(prod)["SEED_SAMPLE_DATA"] == "false"
    assert cfg(prod)["ENVIRONMENT"] == "production"
    hpa = {d["metadata"]["name"]: d["spec"] for d in prod if d["kind"] == "HorizontalPodAutoscaler"}
    assert hpa["backend-blue"]["minReplicas"] == 3
    ing = next(d for d in prod if d["kind"] == "Ingress")
    assert ing["spec"]["tls"][0]["secretName"] == "devsecops360-tls"
    assert "devsecops360-prod-rate-limit" in ing["metadata"]["annotations"][
        "traefik.ingress.kubernetes.io/router.middlewares"]


def test_networkpolicies_isolate_database():
    docs = render.build(ROOT / "kubernetes/overlays/development")
    pg = next(d for d in docs if d["kind"] == "NetworkPolicy" and d["metadata"]["name"] == "postgres")
    allowed = [p["podSelector"]["matchLabels"] for p in pg["spec"]["ingress"][0]["from"]]
    assert {"app.kubernetes.io/name": "backend"} in allowed
    assert pg["spec"]["egress"] == []


def test_monitoring_objects_are_generated_and_in_sync():
    rule = yaml.safe_load((ROOT / "observability/kubernetes/app-monitoring/prometheusrule.yaml").read_text())
    groups = []
    for f in sorted((ROOT / "observability/prometheus/rules").glob("*.yml")):
        groups += yaml.safe_load(f.read_text())["groups"]
    assert rule["spec"]["groups"] == groups, "run: python scripts/generate_observability.py"
    a = json.loads((ROOT / "observability/grafana/dashboards/devsecops360-overview.json").read_text())
    b = json.loads((ROOT / "observability/kubernetes/app-monitoring/devsecops360-overview.json").read_text())
    assert a == b
