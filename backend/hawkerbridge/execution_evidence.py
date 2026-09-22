"""Only present cloud execution claims tied to the app's exact publication.

These are operator-published verification records, not a live workspace poll.
Missing, malformed, failed, or stale records are deliberately unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path


def read_report(path: Path) -> dict | None:
    try:
        if path.stat().st_size > 5 * 1024 * 1024:
            return None
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def verified_execution(
    snapshot: dict,
    fingerprint: str,
    engine_hash: str,
    execution: dict | None,
    evaluation: dict | None,
) -> tuple[dict | None, dict | None]:
    publication = snapshot.get("manifest", {}).get("databricks", {})
    if not isinstance(publication, dict) or not isinstance(execution, dict):
        return None, None
    checks = execution.get("quality_checks")
    valid = (
        execution.get("pipeline_result") == "SUCCESS"
        and execution.get("mlflow_status") == "FINISHED"
        and execution.get("source_fingerprint") == fingerprint
        and execution.get("engine_code_sha256") == engine_hash
        and publication.get("engine_code_sha256") == engine_hash
        and bool(publication.get("publication_id"))
        and execution.get("publication_id") == publication.get("publication_id")
        and bool(publication.get("mlflow_run_id"))
        and execution.get("mlflow_run_id") == publication.get("mlflow_run_id")
        and execution.get("input_mode") == publication.get("input_mode")
        and bool(execution.get("pipeline_run_id"))
        and isinstance(checks, list)
        and bool(checks)
        and all(
            isinstance(check, dict) and check.get("passed") in (True, "true") for check in checks
        )
    )
    if not valid:
        return None, None
    if not isinstance(evaluation, dict):
        return execution, None
    results = evaluation.get("results")
    valid_evaluation = (
        execution.get("scenarios_evaluated") == 9
        and publication.get("evaluation_scenarios") == 9
        and evaluation.get("scenarios_evaluated") == 9
        and evaluation.get("source_fingerprint") == fingerprint
        and evaluation.get("engine_code_sha256") == engine_hash
        and evaluation.get("publication_id") == publication.get("publication_id")
        and evaluation.get("input_mode") == publication.get("input_mode")
        and isinstance(results, list)
        and len(results) == 9
        and all(
            isinstance(row, dict)
            and isinstance(row.get("scenario_id"), str)
            and row.get("source_fingerprint") == fingerprint
            and row.get("engine_code_sha256") == engine_hash
            for row in results
        )
    )
    if valid_evaluation and len({row["scenario_id"] for row in results}) == 9:
        return execution, evaluation
    return execution, None
