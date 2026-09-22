"""Release maintenance must not disable scheduled data deletion."""

import importlib.util
from pathlib import Path

import pytest


def retention_module():
    spec = importlib.util.spec_from_file_location(
        "configure_retention", Path(__file__).parents[1] / "scripts/configure_retention.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dry_run_overrides_only_execution_and_keeps_saved_job(monkeypatch):
    module = retention_module()
    calls = []
    monkeypatch.setattr("sys.argv", ["retention", "--project", "test-project", "--dry-run"])
    monkeypatch.setattr(module, "exists", lambda _: True)
    monkeypatch.setattr(module, "call", calls.append)
    monkeypatch.setattr(module.subprocess, "check_output", lambda *_args, **_kwargs: pytest.fail("Dry inspection must not fetch or redeploy service settings"))
    module.main()
    assert len(calls) == 1
    assert calls[0][:5] == ["gcloud", "run", "jobs", "execute", "hawkerbridge-retention"]
    assert "--args=-m,hawkerbridge.firebase_cleanup,--limit,1000" in calls[0]
    assert not any("--execute" in part for part in calls[0])


def test_dry_run_requires_existing_job_without_provisioning(monkeypatch):
    module = retention_module()
    monkeypatch.setattr("sys.argv", ["retention", "--project", "test-project", "--dry-run"])
    monkeypatch.setattr(module, "exists", lambda _: False)
    monkeypatch.setattr(module, "call", lambda _: pytest.fail("Missing job must not be created by a dry run"))
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2


def test_existing_schedule_uses_update_headers(monkeypatch):
    import json
    module = retention_module()
    calls = []
    monkeypatch.setattr("sys.argv", ["retention", "--project", "test-project"])
    monkeypatch.setattr(module, "exists", lambda _: True)
    monkeypatch.setattr(module, "call", calls.append)
    service = {"spec": {"template": {"spec": {
        "serviceAccountName": "runtime@test-project.iam.gserviceaccount.com",
        "containers": [{"image": "test-image", "env": [{"name": "MODE", "value": "test"}]}],
    }}}}
    monkeypatch.setattr(module.subprocess, "check_output", lambda *_args, **_kwargs: json.dumps(service))
    module.main()
    update = next(call for call in calls if call[:4] == ["gcloud", "scheduler", "jobs", "update"])
    assert "--update-headers" in update and "--headers" not in update
    assert any("--args=-m,hawkerbridge.firebase_cleanup,--limit,1000,--execute" in call for call in calls)
