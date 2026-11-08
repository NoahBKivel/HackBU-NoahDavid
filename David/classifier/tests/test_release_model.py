import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


def release_module():
    path = Path(__file__).resolve().parents[1] / 'scripts/release_model.py'
    spec = importlib.util.spec_from_file_location('release_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deadline_failure_never_reports_verified_readiness(tmp_path, monkeypatch):
    module = release_module()
    notifications = []
    monkeypatch.setattr(module, 'progress', lambda message: None)
    monkeypatch.setattr(module, 'alert', notifications.append)
    monkeypatch.setattr(module.subprocess, 'run', lambda *args, **kwargs: None)
    class Child:
        pid = 123
        def wait(self, timeout):
            raise subprocess.TimeoutExpired('owned-child', timeout)
        def poll(self):
            return None
        def terminate(self):
            pass
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *args, **kwargs: Child())
    config = {'deadline_seconds': 120, 'reserve_seconds': 10, 'required_source': 'kev-tuned'}
    with pytest.raises(TimeoutError):
        module.release(config, tmp_path, False)
    receipt = json.loads((tmp_path / 'release.json').read_text())
    assert receipt['serving_checks_passed'] is False
    assert receipt['error_type'] == 'TimeoutError'
    assert notifications


def test_failed_dev_check_never_starts_live_deployment(tmp_path, monkeypatch):
    module = release_module()
    commands = []
    monkeypatch.setattr(module, 'progress', lambda message: None)
    monkeypatch.setattr(module, 'alert', lambda message: None)
    class Child:
        pid = 123
        def wait(self, timeout):
            return 1
    def spawn(command, **kwargs):
        commands.append(command)
        return Child()
    monkeypatch.setattr(module.subprocess, 'Popen', spawn)
    config = {'deadline_seconds': 120, 'reserve_seconds': 10, 'required_source': 'kev-tuned'}
    with pytest.raises(RuntimeError):
        module.release(config, tmp_path, False)
    receipt = json.loads((tmp_path / 'release.json').read_text())
    assert receipt['serving_checks_passed'] is False
    assert len(commands) == 1
    assert commands[0][commands[0].index('--action') + 1] == 'dev'
