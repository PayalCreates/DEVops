#!/usr/bin/env python3
"""Minimal Kustomize renderer for offline validation (no kustomize binary needed).

Supports exactly the features this repo uses: resources (files/dirs), namespace,
nameSuffix (+ HPA scaleTargetRef reference fix-up), labels (includeSelectors /
includeTemplates), images, inline JSON6902 patches with target kind/name regex,
and configMapGenerator (files, labels, disableNameSuffixHash).

CI uses the real `kustomize build` (see .github/workflows/iac.yml); this script is
for laptops/sandboxes without the binary.

    python scripts/validate/render_kustomize.py kubernetes/overlays/development > out.yaml
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import yaml

CLUSTER_SCOPED = {"Namespace", "ClusterRole", "ClusterRoleBinding", "PersistentVolume",
                  "StorageClass", "CustomResourceDefinition"}
SELECTOR_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job"}


def _pointer(path: str) -> list[str]:
    return [p.replace("~1", "/").replace("~0", "~") for p in path.lstrip("/").split("/")]


def _walk(doc, parts):
    cur = doc
    for p in parts:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur


def apply_json6902(doc: dict, ops: list[dict]) -> None:
    for op in ops:
        parts = _pointer(op["path"])
        parent = _walk(doc, parts[:-1])
        key = parts[-1]
        if op["op"] in ("replace", "add"):
            if isinstance(parent, list):
                if key == "-":
                    parent.append(op["value"])
                elif op["op"] == "add":
                    parent.insert(int(key), op["value"])
                else:
                    parent[int(key)] = op["value"]
            else:
                if op["op"] == "replace" and key not in parent:
                    raise KeyError(f"replace on missing path {op['path']}")
                parent[key] = op["value"]
        elif op["op"] == "remove":
            del parent[int(key) if isinstance(parent, list) else key]
        else:
            raise ValueError(f"unsupported op {op['op']}")


def _matches(doc: dict, target: dict) -> bool:
    if "kind" in target and doc.get("kind") != target["kind"]:
        return False
    if "name" in target and not re.fullmatch(target["name"], doc["metadata"]["name"]):
        return False
    return True


def _add_labels(doc: dict, pairs: dict, selectors: bool, templates: bool) -> None:
    doc.setdefault("metadata", {}).setdefault("labels", {}).update(pairs)
    kind, spec = doc.get("kind"), doc.get("spec", {})
    if kind in SELECTOR_KINDS and (templates or selectors) and "template" in spec:
        spec["template"].setdefault("metadata", {}).setdefault("labels", {}).update(pairs)
    if not selectors:
        return
    if kind in SELECTOR_KINDS and kind != "Job":
        spec.setdefault("selector", {}).setdefault("matchLabels", {}).update(pairs)
    elif kind == "Service":
        spec.setdefault("selector", {}).update(pairs)
    elif kind == "PodDisruptionBudget":
        spec.setdefault("selector", {}).setdefault("matchLabels", {}).update(pairs)


def build(path: Path) -> list[dict]:
    kfile = path / "kustomization.yaml"
    k = yaml.safe_load(kfile.read_text(encoding="utf-8"))
    docs: list[dict] = []
    for res in k.get("resources", []):
        p = (path / res).resolve()
        if p.is_dir():
            docs.extend(build(p))
        else:
            docs.extend(d for d in yaml.safe_load_all(p.read_text(encoding="utf-8")) if d)

    for gen in k.get("configMapGenerator", []):
        data = {}
        for f in gen.get("files", []):
            key, _, src = f.partition("=")
            src = src or key
            data[Path(key).name] = (path / src).read_text(encoding="utf-8")
        cm = {"apiVersion": "v1", "kind": "ConfigMap",
              "metadata": {"name": gen["name"], "labels": gen.get("options", {}).get("labels", {})},
              "data": data}
        docs.append(cm)

    suffix = k.get("nameSuffix", "")
    if suffix:
        for d in docs:
            d["metadata"]["name"] += suffix
            if d["kind"] == "HorizontalPodAutoscaler":
                d["spec"]["scaleTargetRef"]["name"] += suffix

    for lab in k.get("labels", []):
        for d in docs:
            _add_labels(d, lab["pairs"], lab.get("includeSelectors", False),
                        lab.get("includeTemplates", False))

    for patch in k.get("patches", []):
        ops = yaml.safe_load(patch["patch"])
        hits = [d for d in docs if _matches(d, patch.get("target", {}))]
        if not hits:
            raise ValueError(f"{kfile}: patch target matched nothing: {patch.get('target')}")
        for d in hits:
            apply_json6902(d, copy.deepcopy(ops))

    images = {i["name"]: i for i in k.get("images", [])}
    if images:
        for d in docs:
            pod = d.get("spec", {}).get("template", {}).get("spec") or \
                d.get("spec", {}).get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec")
            for c in (pod or {}).get("containers", []) + (pod or {}).get("initContainers", []):
                name = re.split(r"[:@]", c["image"], maxsplit=1)[0]
                if name in images:
                    img = images[name]
                    c["image"] = f"{img.get('newName', name)}:{img['newTag']}" if "newTag" in img \
                        else img.get("newName", name)

    ns = k.get("namespace")
    if ns:
        for d in docs:
            if d["kind"] not in CLUSTER_SCOPED:
                d["metadata"]["namespace"] = ns
            if d["kind"] == "RoleBinding":
                for s in d.get("subjects", []):
                    if s.get("kind") == "ServiceAccount":
                        s["namespace"] = ns
    return docs


if __name__ == "__main__":
    out = build(Path(sys.argv[1]).resolve())
    sys.stdout.write(yaml.safe_dump_all(out, sort_keys=False))
