#!/usr/bin/env python3
"""A stateful fake `kubectl` used to test the blue-green / rollback scripts' control
flow without a cluster. State lives in $FAKE_KUBE_STATE (JSON); every call is
appended to $FAKE_KUBE_LOG.

Failure injection (env):
  FAKE_FAIL_ROLLOUT=green          rollout status of backend-green fails
  FAKE_FAIL_SMOKE=<substring>      smoke pods whose command contains <substring> fail
"""

import json
import os
import re
import sys

STATE = os.environ["FAKE_KUBE_STATE"]
LOG = os.environ["FAKE_KUBE_LOG"]


def load():
    with open(STATE) as f:
        return json.load(f)


def save(s):
    with open(STATE, "w") as f:
        json.dump(s, f)


def main(argv):
    with open(LOG, "a") as f:
        f.write(" ".join(argv) + "\n")
    s = load()
    args = list(argv)
    if args[:1] == ["-n"]:
        args = args[2:]
    verb = args[0]

    def jsonpath():
        for a in args:
            if a.startswith("jsonpath="):
                return a[len("jsonpath="):]
        if "-o" in args:
            v = args[args.index("-o") + 1]
            return v[len("jsonpath="):] if v.startswith("jsonpath=") else None
        return None

    if verb == "get":
        kind, name = args[1], args[2]
        jp = jsonpath()
        if kind == "svc":
            print(s["services"][name]["color"], end="")
        elif kind == "deploy":
            d = s["deployments"][name]
            if jp == "{.spec.replicas}":
                print(d["replicas"], end="")
            elif jp == "{.status.readyReplicas}":
                print(d["ready"] if d["ready"] else "", end="")
            elif "image" in jp:
                print(d["image"], end="")
        elif kind == "pod":
            print(s["pods"].get(name, "Failed"), end="")
        elif kind == "job":
            sys.exit(0 if name in s["jobs"] else 1)
        return 0

    if verb == "apply":
        doc = sys.stdin.read()
        if "kind: Pod" in doc:
            name = re.search(r"name: (smoke-\S+)", doc).group(1)
            cmd = re.search(r"command: \[(.*)\]", doc).group(1)
            fail = os.getenv("FAKE_FAIL_SMOKE")
            s["pods"][name] = "Failed" if fail and fail in cmd else "Succeeded"
            s["smoke_runs"].append({"cmd": cmd, "result": s["pods"][name]})
        elif "kind: Job" in doc:
            image = re.search(r"image: (\S+)", doc).group(1)
            s["jobs"]["db-migrate"] = image
        save(s)
        return 0

    if verb == "create":  # configmap --dry-run=client -o yaml
        print("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: smoke-check\n")
        return 0

    if verb == "wait":
        return 0 if "db-migrate" in s["jobs"] else 1

    if verb == "set":  # set image deploy/backend-green backend=IMG
        name = args[2].split("/")[1]
        s["deployments"][name]["image"] = args[3].split("=", 1)[1]
        save(s)
        return 0

    if verb == "scale":
        name = args[1].split("/")[1]
        n = int(next(a for a in args if a.startswith("--replicas=")).split("=")[1])
        s["deployments"][name]["replicas"] = n
        s["deployments"][name]["ready"] = n
        save(s)
        return 0

    if verb == "rollout":
        name = args[2].split("/")[1]
        if os.getenv("FAKE_FAIL_ROLLOUT") and name.endswith(os.environ["FAKE_FAIL_ROLLOUT"]):
            s["deployments"][name]["ready"] = 0
            save(s)
            return 1
        return 0

    if verb == "patch":
        name = args[2]
        body = json.loads(args[args.index("-p") + 1])
        s["services"][name]["color"] = body["spec"]["selector"]["devsecops360/color"]
        s["switches"].append({name: s["services"][name]["color"]})
        save(s)
        return 0

    if verb in ("delete", "annotate", "logs"):
        return 0

    print(f"fake kubectl: unsupported {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
