"""Read back real cloud outputs and export credential-free deployment evidence.

Run after the bundle job succeeds. This is a verification/export command, not
an ingestion fallback, a browser test, or proof of observed social impact.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from databricks.sdk import WorkspaceClient  # noqa: E402
from hawkerbridge.config import Settings  # noqa: E402
from hawkerbridge.databricks_store import DatabricksStore  # noqa: E402
from hawkerbridge.engine import PlanningEngine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="DAISI")
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--catalog", default="workspace")
    parser.add_argument("--schema", default="hawkerbridge")
    parser.add_argument("--pipeline-run-id", required=True, type=int)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "tmp")
    args = parser.parse_args()
    client = WorkspaceClient(profile=args.profile)
    run = client.jobs.get_run(args.pipeline_run_id)
    if not run.state or getattr(run.state.result_state, "value", None) != "SUCCESS":
        raise RuntimeError("The supplied pipeline run has not completed successfully")
    store = DatabricksStore(
        Settings(
            databricks_warehouse_id=args.warehouse_id, catalog=args.catalog, schema=args.schema
        ),
        client=client,
        timeout_seconds=120,
    )
    snapshot = store.load_snapshot()
    task = next(
        (
            task
            for task in (run.tasks or [])
            if task.task_key == "ingest_validate_evaluate_publish"
            and getattr(task.state.result_state, "value", None) == "SUCCESS"
        ),
        None,
    )
    if task is None:
        raise RuntimeError("The supplied run has no successful HawkerBridge publication task")
    output = client.jobs.get_run_output(task.run_id).notebook_output
    if output is None or output.truncated or not output.result:
        raise RuntimeError("The successful task has no complete publication report")
    report = json.loads(output.result)
    publication = snapshot["manifest"].get("databricks", {})
    if report.get("status") != "PUBLISHED" or report.get("publication_id") != publication.get(
        "publication_id"
    ):
        raise RuntimeError("The latest SQL snapshot does not belong to the supplied run")
    fingerprint = PlanningEngine(snapshot).fingerprint
    evaluation = store.load_evaluation(fingerprint)
    baseline = json.loads((ROOT / "data/processed/snapshot.json").read_text())
    checksums = {row["key"]: row["sha256"] for row in baseline["manifest"]["sources"]}
    comparison = [
        {
            "source": row["key"],
            "sha256": row["sha256"],
            "matches_local_source": row["sha256"] == checksums.get(row["key"]),
            "fetched_at": row["fetched_at"],
            "reused_at": row.get("reused_at"),
            "mirror": row.get("mirror", False),
        }
        for row in snapshot["manifest"]["sources"]
    ]
    dashboard = json.loads(
        (ROOT / "databricks/dashboard/hawkerbridge-evidence.lvdash.json").read_text()
    )
    dashboard_results = []
    for dataset in dashboard["datasets"]:
        query = re.sub(
            r"\b(FROM|JOIN)\s+(published_[a-z_]+)\b",
            lambda match: f"{match[1]} {store.namespace}.{match[2]}",
            dataset["query"],
            flags=re.IGNORECASE,
        )
        rows = store._execute(query)
        dashboard_results.append(
            {
                "name": dataset["name"],
                "row_count": len(rows),
                "columns": list(rows[0]) if rows else [],
            }
        )
    counts = store._execute(
        f"SELECT count(*) AS centres, sum(CASE WHEN food_stalls > 0 THEN 1 ELSE 0 END) AS food_centres "
        f"FROM {store.namespace}.published_centres"
    )[0]
    bronze_integrity = store._execute(
        "SELECT count(*) AS sources, "
        "sum(CASE WHEN sha2(payload_json, 256) = sha256 "
        "AND octet_length(payload_json) = byte_count THEN 1 ELSE 0 END) AS verified_payloads "
        f"FROM {store.namespace}.published_bronze_sources"
    )[0]
    if int(bronze_integrity["sources"]) != len(comparison) or (
        bronze_integrity["sources"] != bronze_integrity["verified_payloads"]
    ):
        raise RuntimeError("Bronze payload bytes do not match the published source checksums")
    audits = store._execute(
        f"SELECT check_name, passed, observed_value FROM {store.namespace}.published_quality_audit"
    )
    if not {"budget_violations", "below_baseline_cases"}.issubset(
        {row["check_name"] for row in audits}
    ) or any(str(row["passed"]).lower() != "true" for row in audits):
        raise RuntimeError("A published quality check is not true")
    mlflow_run_id = snapshot["manifest"]["databricks"]["mlflow_run_id"]
    mlflow_run = client.experiments.get_run(mlflow_run_id).run
    if not mlflow_run or mlflow_run.info.status.value != "FINISHED":
        raise RuntimeError("The published MLflow parent run is not finished")
    child_ids = [result["mlflow_run_id"] for result in evaluation["results"]]
    if len(set(child_ids)) != evaluation["scenarios_evaluated"]:
        raise RuntimeError("Each evaluated scenario must have a distinct MLflow run")
    for result in evaluation["results"]:
        child = client.experiments.get_run(result["mlflow_run_id"]).run
        if not child or child.info.status.value != "FINISHED":
            raise RuntimeError("An evaluated scenario has no finished MLflow run")
        tags = {tag.key: tag.value for tag in (child.data.tags or [])}
        metrics = {metric.key: metric.value for metric in (child.data.metrics or [])}
        if tags.get("mlflow.parentRunId") != mlflow_run_id:
            raise RuntimeError("A scenario belongs to a different MLflow publication")
        expected = {
            "planned_meals": result["summary"]["total_meals"],
            "spent_sgd": result["summary"]["spent"],
            "weighted_benefit": result["summary"]["weighted_benefit"],
            "baseline_weighted_benefit": result["baseline"]["weighted_benefit"],
        }
        if any(
            key not in metrics or abs(metrics[key] - value) > 1e-7
            for key, value in expected.items()
        ):
            raise RuntimeError("A scenario's MLflow metrics do not match its published result")
    evidence = {
        "verified_at": datetime.now(UTC).isoformat(),
        "workspace_host": client.config.host,
        "pipeline_run_id": args.pipeline_run_id,
        "pipeline_run_url": run.run_page_url,
        "pipeline_result": run.state.result_state.value,
        "publication_id": evaluation["publication_id"],
        "input_mode": evaluation["input_mode"],
        "source_fingerprint": fingerprint,
        "engine_code_sha256": evaluation["engine_code_sha256"],
        "local_snapshot_fingerprint": PlanningEngine(baseline).fingerprint,
        "source_comparison": comparison,
        "published_counts": counts,
        "bronze_payload_integrity": bronze_integrity,
        "scenarios_evaluated": evaluation["scenarios_evaluated"],
        "quality_checks": audits,
        "dashboard_queries": dashboard_results,
        "mlflow_run_id": mlflow_run_id,
        "mlflow_experiment_id": mlflow_run.info.experiment_id,
        "mlflow_status": mlflow_run.info.status.value,
        "mlflow_child_runs_verified": len(child_ids),
        "scope": "Actual Databricks processing and query evidence. No browser or field-impact verification.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("snapshot", snapshot),
        ("evaluation", evaluation),
        ("evidence", evidence),
    ):
        destination = args.output_dir / f"databricks-published-{name}.json"
        destination.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        )
        print(destination)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
