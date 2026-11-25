#!/usr/bin/env python3
"""Offline Terraform checks for machines without the terraform binary:
1) every .tf file parses as HCL2; 2) every module call passes only declared
variables and sets every required variable. CI runs the real `terraform validate`.

    pip install python-hcl2 && python scripts/validate/terraform_static_check.py
"""
import pathlib
import sys

import hcl2

ROOT = pathlib.Path(__file__).resolve().parents[2] / "terraform"
IGNORE = {"source", "depends_on", "providers", "count", "for_each", "__is_block__"}
clean = lambda k: k.strip('"')  # noqa: E731


def load(f):
    with open(f, encoding="utf-8") as fh:
        return hcl2.load(fh)


def variables(module_dir):
    out = {}
    for f in module_dir.glob("*.tf"):
        for v in load(f).get("variable", []):
            name, body = next(iter(v.items()))
            out[clean(name)] = "default" in {clean(k) for k in body}
    return out


errors, files = 0, 0
for f in sorted(ROOT.rglob("*.tf")):
    files += 1
    try:
        load(f)
    except Exception as e:  # noqa: BLE001
        errors += 1
        print(f"PARSE FAIL {f}: {e}")

for f in sorted((ROOT / "environments").rglob("main.tf")):
    for m in load(f).get("module", []):
        name, body = next(iter(m.items()))
        src = (f.parent / clean(body["source"])).resolve()
        declared = variables(src)
        passed = {clean(k) for k in body} - IGNORE
        unknown = passed - declared.keys()
        missing = {k for k, has_default in declared.items() if not has_default} - passed
        status = "OK " if not (unknown or missing) else "FAIL"
        errors += bool(unknown or missing)
        print(f"[{status}] {f.relative_to(ROOT)} module {clean(name)} -> {src.name}"
              + (f" unknown={sorted(unknown)}" if unknown else "")
              + (f" missing={sorted(missing)}" if missing else ""))

print(f"{files} .tf files parsed; {errors} error(s)")
sys.exit(1 if errors else 0)
