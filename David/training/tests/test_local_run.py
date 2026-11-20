"""Verify that local resource limits fail closed and leases release reliably."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "local_run.py"
SPEC = importlib.util.spec_from_file_location("local_run", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def paths(tmp_path):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"worker_limit": 2, "minimum_available_gib": 4,
                                  "legacy_reservations": 1}), encoding="utf-8")
    return policy, tmp_path / "state.json"


def test_low_ram_never_creates_lease(paths, monkeypatch):
    monkeypatch.setattr(MODULE, "available_gib", lambda: 3.9)
    with pytest.raises(RuntimeError, match="RAM gate closed"):
        with MODULE.lease(*paths, "blocked", 0):
            pytest.fail("A blocked worker ran.")
    assert not paths[1].exists()


def test_memory_allowance_preserves_headroom(paths, monkeypatch):
    monkeypatch.setattr(MODULE, "available_gib", lambda: 4.1)
    with pytest.raises(RuntimeError, match="RAM gate closed"):
        with MODULE.lease(*paths, "too-large", 256):
            pytest.fail("A worker exceeded available headroom.")


def test_legacy_and_live_leases_share_limit(paths, monkeypatch):
    monkeypatch.setattr(MODULE, "available_gib", lambda: 8)
    with MODULE.lease(*paths, "first", 128):
        with pytest.raises(RuntimeError, match="worker limit"):
            with MODULE.lease(*paths, "second", 128):
                pytest.fail("The worker cap was exceeded.")
    assert json.loads(paths[1].read_text()) == {}


def test_lease_releases_on_failure(paths, monkeypatch):
    monkeypatch.setattr(MODULE, "available_gib", lambda: 8)
    with pytest.raises(ValueError):
        with MODULE.lease(*paths, "failed", 128):
            raise ValueError("Expected worker failure.")
    assert json.loads(paths[1].read_text()) == {}
