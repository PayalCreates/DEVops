"""Tests for the blue-green deploy and rollback scripts' decision logic.

Runs the REAL bash scripts against a stateful fake `kubectl` (fake_kubectl.py), so
we can prove: a healthy release switches traffic; a failed rollout or failed
pre-switch smoke test never switches; a failed post-switch verification rolls
back automatically; rollback flips back. (On a real cluster, the delivery
pipeline exercises the same scripts end-to-end on kind.)
"""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deployment/scripts/blue-green-deploy.sh"
ROLLBACK = ROOT / "deployment/rollback/rollback.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")


@pytest.fixture()
def kube(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    shim = bindir / "kubectl"
    shim.write_text(f"#!/bin/sh\nexec python3 {ROOT / 'tests/deployment/fake_kubectl.py'} \"$@\"\n")
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    state = tmp_path / "state.json"
    state.write_text(json.dumps({
        "services": {"backend": {"color": "blue"}, "backend-preview": {"color": "green"}},
        "deployments": {
            "backend-blue": {"replicas": 2, "ready": 2, "image": "devsecops360-backend:v1"},
            "backend-green": {"replicas": 0, "ready": 0, "image": "devsecops360-backend:v1"},
        },
        "jobs": {}, "pods": {}, "smoke_runs": [], "switches": [],
    }))
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "NAMESPACE": "test-ns",
           "FAKE_KUBE_STATE": str(state), "FAKE_KUBE_LOG": str(tmp_path / "calls.log")}

    def run(script, *args, **extra_env):
        p = subprocess.run(["bash", str(script), *args], env={**env, **extra_env},
                           capture_output=True, text=True, timeout=60)
        return p, json.loads(state.read_text())

    # the scripts sleep a few seconds for kube-proxy; make that instant in tests
    monkeypatch.setenv("PATH", env["PATH"])
    sleep = bindir / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    return run


def test_healthy_release_switches_to_idle_colour(kube):
    p, s = kube(DEPLOY, "devsecops360-backend:v2")
    assert p.returncode == 0, p.stderr + p.stdout
    assert s["services"]["backend"]["color"] == "green"
    assert s["services"]["backend-preview"]["color"] == "blue"
    assert s["deployments"]["backend-green"]["image"] == "devsecops360-backend:v2"
    assert s["deployments"]["backend-green"]["replicas"] == 2       # matched active size
    assert s["deployments"]["backend-blue"]["replicas"] == 2        # old colour kept for rollback
    assert s["jobs"]["db-migrate"] == "devsecops360-backend:v2"     # migrated with NEW image
    # pre-switch smoke went to preview, post-switch through the frontend
    assert "backend-preview:8000" in s["smoke_runs"][0]["cmd"]
    assert "frontend:8080" in s["smoke_runs"][1]["cmd"]
    assert '"event":"blue_green_deploy","result":"success"' in p.stdout


def test_failed_rollout_never_switches(kube):
    p, s = kube(DEPLOY, "devsecops360-backend:broken", FAKE_FAIL_ROLLOUT="green")
    assert p.returncode != 0
    assert s["services"]["backend"]["color"] == "blue"
    assert s["switches"] == []
    assert "traffic still on blue" in p.stderr


def test_failed_preswitch_smoke_never_switches(kube):
    p, s = kube(DEPLOY, "devsecops360-backend:bad", FAKE_FAIL_SMOKE="backend-preview")
    assert p.returncode != 0
    assert s["services"]["backend"]["color"] == "blue"
    assert s["switches"] == []
    assert "pre-switch smoke test FAILED" in p.stderr


def test_failed_postswitch_verification_auto_rolls_back(kube):
    p, s = kube(DEPLOY, "devsecops360-backend:v2", FAKE_FAIL_SMOKE='"http://frontend:8080", "green"')
    assert p.returncode != 0
    assert [sw.get("backend") for sw in s["switches"] if "backend" in sw] == ["green", "blue"]
    assert s["services"]["backend"]["color"] == "blue"
    assert "deployment rolled back" in p.stderr


def test_scale_down_old_frees_capacity(kube):
    p, s = kube(DEPLOY, "devsecops360-backend:v2", SCALE_DOWN_OLD="true")
    assert p.returncode == 0, p.stderr
    assert s["deployments"]["backend-blue"]["replicas"] == 0


def test_rollback_flips_back_and_scales_up_if_needed(kube):
    kube(DEPLOY, "devsecops360-backend:v2", SCALE_DOWN_OLD="true")
    p, s = kube(ROLLBACK)
    assert p.returncode == 0, p.stderr + p.stdout
    assert s["services"]["backend"]["color"] == "blue"
    assert s["deployments"]["backend-blue"]["replicas"] >= 1
    assert '"event":"rollback","result":"success"' in p.stdout
