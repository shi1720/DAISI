"""Cloud claims must match the exact active snapshot, code, and publication."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hawkerbridge.api import create_app
from hawkerbridge.config import Settings
from hawkerbridge.engine import PlanningEngine
from hawkerbridge.execution_evidence import read_report, verified_execution


@pytest.fixture
def reports():
    snapshot = json.loads(Settings().data_path.read_text())
    engine_hash = hashlib.sha256(
        Path(__file__).parents[1].joinpath("backend/hawkerbridge/engine.py").read_bytes()
    ).hexdigest()
    snapshot["manifest"]["databricks"] = {
        "publication_id": "verified-publication",
        "input_mode": "live",
        "mlflow_run_id": "parent-run",
        "engine_code_sha256": engine_hash,
        "evaluation_scenarios": 9,
    }
    fingerprint = PlanningEngine(snapshot).fingerprint
    execution = {
        "pipeline_result": "SUCCESS",
        "mlflow_status": "FINISHED",
        "pipeline_run_id": 123,
        "publication_id": "verified-publication",
        "mlflow_run_id": "parent-run",
        "input_mode": "live",
        "engine_code_sha256": engine_hash,
        "source_fingerprint": fingerprint,
        "scenarios_evaluated": 9,
        "quality_checks": [{"check_name": "budget_violations", "passed": "true"}],
    }
    evaluation = {
        "source_fingerprint": fingerprint,
        "engine_code_sha256": engine_hash,
        "publication_id": "verified-publication",
        "input_mode": "live",
        "scenarios_evaluated": 9,
        "results": [
            {
                "scenario_id": str(i),
                "source_fingerprint": fingerprint,
                "engine_code_sha256": engine_hash,
            }
            for i in range(9)
        ],
    }
    return snapshot, fingerprint, engine_hash, execution, evaluation


def test_verified_cloud_execution_and_nine_results_are_exposed(reports):
    assert verified_execution(*reports) == (reports[3], reports[4])


@pytest.mark.parametrize(
    "field,value",
    [
        ("pipeline_result", "FAILED"),
        ("mlflow_status", "RUNNING"),
        ("source_fingerprint", "stale"),
        ("engine_code_sha256", "old-code"),
        ("publication_id", "other-publication"),
        ("mlflow_run_id", "different-parent"),
        ("input_mode", "snapshot"),
        ("pipeline_run_id", None),
        ("quality_checks", []),
        ("quality_checks", [{"passed": "false"}]),
    ],
)
def test_failed_or_stale_execution_never_inherits_valid_cloud_report(reports, field, value):
    snapshot, fingerprint, engine_hash, execution, evaluation = reports
    execution[field] = value
    assert verified_execution(snapshot, fingerprint, engine_hash, execution, evaluation) == (
        None,
        None,
    )


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "source",
        "code",
        "publication",
        "count",
        "short",
        "duplicate",
        "row-code",
        "row-source",
    ],
)
def test_cloud_evaluation_is_independently_guarded(reports, change):
    snapshot, fingerprint, engine_hash, execution, evaluation = reports
    if change == "missing":
        evaluation = None
    elif change in {"source", "code", "publication"}:
        evaluation[
            {
                "source": "source_fingerprint",
                "code": "engine_code_sha256",
                "publication": "publication_id",
            }[change]
        ] = "mismatch"
    elif change == "count":
        evaluation["scenarios_evaluated"] = 15
    elif change == "short":
        evaluation["results"].pop()
    elif change == "duplicate":
        evaluation["results"][-1] = deepcopy(evaluation["results"][0])
    elif change == "row-code":
        evaluation["results"][0]["engine_code_sha256"] = "mismatch"
    elif change == "row-source":
        evaluation["results"][0]["source_fingerprint"] = "mismatch"
    assert verified_execution(snapshot, fingerprint, engine_hash, execution, evaluation) == (
        execution,
        None,
    )


def test_snapshot_requires_matching_publication_even_if_sources_match(reports):
    snapshot, fingerprint, engine_hash, execution, evaluation = reports
    snapshot["manifest"]["databricks"]["publication_id"] = "another-run-same-sources"
    assert verified_execution(snapshot, fingerprint, engine_hash, execution, evaluation) == (
        None,
        None,
    )
    snapshot["manifest"].pop("databricks")
    assert verified_execution(snapshot, fingerprint, engine_hash, execution, evaluation) == (
        None,
        None,
    )


def test_missing_malformed_and_nonobject_artifacts_are_unavailable(tmp_path):
    path = tmp_path / "report.json"
    assert read_report(path) is None
    for data in ("{broken", "[]", "null"):
        path.write_text(data)
        assert read_report(path) is None


def test_api_keeps_local_benchmark_separate_from_cloud_and_hides_removed_proof(tmp_path, reports):
    snapshot, fingerprint, engine_hash, execution, cloud = reports
    paths = {key: tmp_path / f"{key}.json" for key in ("snapshot", "local", "execution", "cloud")}
    local = {
        "source_fingerprint": fingerprint,
        "engine_code_sha256": engine_hash,
        "scenarios_evaluated": 15,
        "results": [{"scenario_id": "local-report"}],
    }
    for key, value in (
        ("snapshot", snapshot),
        ("local", local),
        ("execution", execution),
        ("cloud", cloud),
    ):
        paths[key].write_text(json.dumps(value))
    settings = replace(
        Settings(),
        database_path=tmp_path / "isolated.db",
        data_path=paths["snapshot"],
        evaluation_path=paths["local"],
        databricks_evaluation_path=paths["cloud"],
        databricks_publication_path=paths["execution"],
    )
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/auth/demo", json={}).status_code == 200
        body = client.get("/api/evidence").json()
        assert body["evaluation"] == local and body["evaluation_execution"] == "local"
        assert body["cloud_evaluation"] == cloud and body["workspace_execution"] == execution
        paths["execution"].unlink()
        unavailable = client.get("/api/evidence").json()
        assert (
            unavailable["workspace_execution"] is None and unavailable["cloud_evaluation"] is None
        )
        assert unavailable["evaluation"] == local
        paths["execution"].write_text("{broken")
        assert client.get("/api/evidence").json()["workspace_execution"] is None
