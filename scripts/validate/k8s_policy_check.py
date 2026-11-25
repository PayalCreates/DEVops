#!/usr/bin/env python3
"""Policy-as-code checks on rendered Kubernetes manifests.

Encodes the platform's security & reliability rules (the same ones a Kyverno or
Gatekeeper policy would enforce in-cluster) and fails CI on any violation.

    python scripts/validate/k8s_policy_check.py rendered-dev.yaml [more.yaml ...]
"""

import sys
from pathlib import Path

import yaml

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}


def pod_spec(d: dict) -> dict | None:
    s = d.get("spec", {})
    if d["kind"] == "CronJob":
        return s["jobTemplate"]["spec"]["template"]["spec"]
    return s.get("template", {}).get("spec")


def check(docs: list[dict]) -> list[str]:
    errs: list[str] = []
    kinds = {(d["kind"], d["metadata"]["name"]) for d in docs}
    services = {d["metadata"]["name"]: d for d in docs if d["kind"] == "Service"}
    deployments = [d for d in docs if d["kind"] == "Deployment"]

    if ("NetworkPolicy", "default-deny-all") not in kinds:
        errs.append("namespace has no default-deny-all NetworkPolicy")
    ns = [d for d in docs if d["kind"] == "Namespace"]
    for n in ns:
        if n["metadata"].get("labels", {}).get("pod-security.kubernetes.io/enforce") != "restricted":
            errs.append(f"Namespace {n['metadata']['name']}: PSA enforce must be 'restricted'")

    for d in docs:
        if d["kind"] not in WORKLOADS:
            continue
        ref = f"{d['kind']}/{d['metadata']['name']}"
        spec = pod_spec(d)
        psc = spec.get("securityContext", {})
        if spec.get("automountServiceAccountToken") is not False and d["metadata"]["name"] != "deployer":
            errs.append(f"{ref}: automountServiceAccountToken must be false")
        if not psc.get("runAsNonRoot"):
            errs.append(f"{ref}: pod securityContext.runAsNonRoot must be true")
        if psc.get("seccompProfile", {}).get("type") != "RuntimeDefault":
            errs.append(f"{ref}: seccompProfile RuntimeDefault required")
        for c in spec.get("containers", []):
            cref = f"{ref}[{c['name']}]"
            sc = c.get("securityContext", {})
            if sc.get("allowPrivilegeEscalation") is not False:
                errs.append(f"{cref}: allowPrivilegeEscalation must be false")
            if sc.get("readOnlyRootFilesystem") is not True:
                errs.append(f"{cref}: readOnlyRootFilesystem must be true")
            if "ALL" not in sc.get("capabilities", {}).get("drop", []):
                errs.append(f"{cref}: must drop ALL capabilities")
            res = c.get("resources", {})
            if not res.get("requests") or not res.get("limits", {}).get("memory"):
                errs.append(f"{cref}: CPU/memory requests and a memory limit are required")
            img = c["image"]
            if img.endswith(":latest") and d["metadata"].get("namespace", "").endswith("-prod"):
                errs.append(f"{cref}: ':latest' tag not allowed in production ({img})")
            if d["kind"] in {"Deployment", "StatefulSet"}:
                for probe in ("readinessProbe", "livenessProbe"):
                    if probe not in c:
                        errs.append(f"{cref}: {probe} missing")

    # Blue-green invariants
    for name in ("backend", "backend-preview"):
        if name not in services:
            errs.append(f"blue-green: Service {name} missing")
    if {"backend", "backend-preview"} <= services.keys():
        a = services["backend"]["spec"]["selector"].get("devsecops360/color")
        p = services["backend-preview"]["spec"]["selector"].get("devsecops360/color")
        if not a or not p or a == p:
            errs.append(f"blue-green: active ({a}) and preview ({p}) must select different colours")
    for color in ("blue", "green"):
        dep = next((x for x in deployments if x["metadata"]["name"] == f"backend-{color}"), None)
        if dep is None:
            errs.append(f"blue-green: Deployment backend-{color} missing")
            continue
        sel = dep["spec"]["selector"]["matchLabels"]
        tpl = dep["spec"]["template"]["metadata"]["labels"]
        if sel.get("devsecops360/color") != color or tpl.get("devsecops360/color") != color:
            errs.append(f"backend-{color}: selector/template must carry devsecops360/color={color}")
        env = {e["name"]: e.get("value") for e in dep["spec"]["template"]["spec"]["containers"][0]["env"]}
        if env.get("APP_COLOR") != color:
            errs.append(f"backend-{color}: APP_COLOR env is {env.get('APP_COLOR')!r}")
    hpas = {d["spec"]["scaleTargetRef"]["name"] for d in docs if d["kind"] == "HorizontalPodAutoscaler"}
    for color in ("blue", "green"):
        if f"backend-{color}" not in hpas:
            errs.append(f"HPA for backend-{color} missing or targets wrong name")
    return errs


def main() -> int:
    failed = 0
    for f in sys.argv[1:]:
        docs = [d for d in yaml.safe_load_all(Path(f).read_text(encoding="utf-8")) if d]
        errs = check(docs)
        status = "OK " if not errs else "FAIL"
        print(f"[{status}] {f}: {len(docs)} objects, {len(errs)} violation(s)")
        for e in errs:
            print(f"   - {e}")
        failed += bool(errs)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
