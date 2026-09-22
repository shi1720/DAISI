"""Serverless publication pipeline. Importable locally; Spark/MLflow load at runtime.

Publication is a final append to gold_snapshots, not a multi-table transaction.
All intermediate rows carry a publication_id. Readers must use published_* views
or filter by the latest gold_snapshots ID, so interrupted staging is not exposed.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import tempfile
import time
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
# These dates and budgets are declared before evaluating results, not selected by uplift.
EVALUATION_DATES = ("2026-09-22", "2026-10-05", "2026-12-14")
EVALUATION_BUDGETS = (600, 1500, 3000)

TABLES = {
    "bronze_sources": (
        "publication_id STRING, source_key STRING, dataset_id STRING, source_url STRING, "
        "transport_url STRING, source_fetched_at STRING, archived_reused_at STRING, mirror BOOLEAN, "
        "sha256 STRING, byte_count BIGINT, payload_json STRING, ingested_at TIMESTAMP",
        "Archived source payloads with original retrieval metadata and SHA-256. Public data only.",
    ),
    "silver_centres": (
        "publication_id STRING, id STRING, name STRING, lat DOUBLE, lng DOUBLE, address STRING, "
        "planning_area STRING, food_stalls BIGINT, market_stalls BIGINT",
        "NEA hawker infrastructure. Stall counts do not measure operating capacity.",
    ),
    "silver_closures": (
        "publication_id STRING, id STRING, centre_id STRING, start_date DATE, end_date DATE, "
        "kind STRING, source_text STRING",
        "Resolved centre-level closure intervals. Missing and partial dates remain in quarantine.",
    ),
    "silver_demand_zones": (
        "publication_id STRING, id STRING, name STRING, planning_area STRING, lat DOUBLE, lng DOUBLE, "
        "residents BIGINT, seniors BIGINT, population_year INT, location_method STRING, geometry_json STRING",
        "Census 2020 subzone counts at polygon representative points, not individuals or homes.",
    ),
    "silver_boundaries": (
        "publication_id STRING, id STRING, planning_area STRING, geometry_json STRING",
        "Master Plan 2019 planning-area polygons simplified for display, not route inference.",
    ),
    "silver_food_waste": (
        "publication_id STRING, year INT, generated_tonnes BIGINT, recycled_tonnes BIGINT, "
        "disposed_tonnes BIGINT, recycling_rate_percent DOUBLE",
        "National annual food-waste context. No centre-level attribution or avoided-waste claim.",
    ),
    "silver_quarantine": (
        "publication_id STRING, id STRING, centre_id STRING, kind STRING, source_start STRING, "
        "source_end STRING, source_text STRING, reason STRING",
        "Unresolved source intervals retained for operator review, never treated as confirmed open.",
    ),
    "gold_access_by_area": (
        "publication_id STRING, evaluation_date DATE, planning_area STRING, residents BIGINT, seniors BIGINT, "
        "newly_exposed_residents BIGINT, newly_exposed_seniors BIGINT, coverage_pct DOUBLE, "
        "centres BIGINT, closed_centres BIGINT, radius_m DOUBLE, source_fingerprint STRING",
        "Scenario screen: population of subzones whose representative points lose nearby hawker coverage.",
    ),
    "gold_access_zones": (
        "publication_id STRING, evaluation_date DATE, zone_id STRING, planning_area STRING, "
        "baseline_distance_m DOUBLE, current_distance_m DOUBLE, baseline_covered BOOLEAN, "
        "current_covered BOOLEAN, newly_exposed BOOLEAN, priority_score DOUBLE, source_fingerprint STRING",
        "Great-circle proximity screen. Distances are not walkability or accessibility guarantees.",
    ),
    "gold_evaluations": (
        "publication_id STRING, scenario_id STRING, evaluation_date DATE, budget DOUBLE, spent DOUBLE, "
        "planned_meals BIGINT, estimated_demand BIGINT, weighted_benefit DOUBLE, "
        "baseline_weighted_benefit DOUBLE, improvement_pct DOUBLE, solver_status STRING, "
        "runtime_seconds DOUBLE, parameters_json STRING, result_json STRING, mlflow_run_id STRING, "
        "source_fingerprint STRING",
        "Measured optimiser versus largest-demand-first baseline on declared scenario assumptions; no field outcomes.",
    ),
    "quality_audit": (
        "publication_id STRING, check_name STRING, passed BOOLEAN, observed_value DOUBLE, "
        "detail STRING, checked_at TIMESTAMP",
        "Publication gates and visible quarantine counts. Failed gates prevent snapshot publication.",
    ),
    "lineage_edges": (
        "publication_id STRING, parent_asset STRING, child_asset STRING, transformation STRING, "
        "recorded_at TIMESTAMP",
        "Explicit application lineage for Python transformations. SQL view lineage is additionally captured by Unity Catalog.",
    ),
    "pipeline_events": (
        "publication_id STRING, event STRING, input_mode STRING, detail STRING, recorded_at TIMESTAMP",
        "Append-only run audit, including failed runs. No credential or raw exception payloads.",
    ),
    "gold_snapshots": (
        "publication_id STRING, snapshot_json STRING, created_at TIMESTAMP, source_fingerprint STRING, "
        "input_mode STRING, mlflow_run_id STRING",
        "Published app inputs; appended only after structured tables, quality gates and MLflow evaluation succeed.",
    ),
    "application_plans": (
        "owner_id STRING, plan_id STRING, plan_json STRING, updated_at TIMESTAMP",
        "Saved planning proposals. Access through authenticated app owner filters; not dispatched services.",
    ),
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def namespace(catalog: str, schema: str) -> str:
    if any(not IDENTIFIER.fullmatch(value) for value in (catalog, schema)):
        raise ValueError("Catalog and schema must be simple SQL identifiers")
    return f"`{catalog}`.`{schema}`"


def bootstrap_tables(spark: Any, catalog: str, schema: str) -> str:
    ns = namespace(catalog, schema)
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {ns} COMMENT 'HawkerBridge open-data continuity planning'")
    for table, (ddl, comment) in TABLES.items():
        spark.sql(f"CREATE TABLE IF NOT EXISTS {ns}.{table} ({ddl}) USING DELTA COMMENT '{comment}'")
    return ns


def append_rows(spark: Any, ns: str, table: str, rows: list[dict]) -> None:
    if rows:
        # Explicit schema works with null values and Spark Connect on serverless.
        spark.createDataFrame(rows, schema=TABLES[table][0]).write.format("delta").mode("append").saveAsTable(f"{ns}.{table}")


def create_published_views(spark: Any, ns: str) -> None:
    for table in ("silver_centres", "silver_closures", "silver_demand_zones", "silver_boundaries",
                  "silver_food_waste", "silver_quarantine", "gold_access_by_area", "gold_access_zones",
                  "gold_evaluations", "quality_audit", "lineage_edges", "bronze_sources"):
        view = "published_" + table.removeprefix("silver_").removeprefix("gold_")
        spark.sql(f"""CREATE OR REPLACE VIEW {ns}.{view} AS
            SELECT data.* FROM {ns}.{table} data
            INNER JOIN (SELECT publication_id FROM {ns}.gold_snapshots
                        ORDER BY created_at DESC, publication_id DESC LIMIT 1) published
            ON data.publication_id = published.publication_id""")
    # DISTINCT prevents overlapping cleaning and works intervals from double-counting a centre.
    spark.sql(f"""CREATE OR REPLACE VIEW {ns}.published_closure_calendar AS
        WITH expanded AS (
            SELECT DISTINCT centre_id,
                explode(sequence(start_date, end_date, INTERVAL 1 DAY)) AS closure_date
            FROM {ns}.published_closures
        )
        SELECT e.closure_date, count(*) AS closed_centres, sum(c.food_stalls) AS food_stalls_closed
        FROM expanded e JOIN {ns}.published_centres c ON e.centre_id = c.id
        GROUP BY e.closure_date""")


def grant_app_permissions(spark: Any, ns: str, catalog: str, app_name: str) -> str:
    from databricks.sdk import WorkspaceClient

    app = WorkspaceClient().apps.get(app_name)
    principal = app.service_principal_client_id
    try:
        principal = str(uuid.UUID(principal or ""))
    except ValueError as exc:
        raise ValueError("App service principal is unavailable; deploy the bundle app resource first") from exc
    spark.sql(f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{principal}`")
    spark.sql(f"GRANT USE SCHEMA ON SCHEMA {ns} TO `{principal}`")
    spark.sql(f"GRANT SELECT ON TABLE {ns}.gold_snapshots TO `{principal}`")
    spark.sql(f"GRANT SELECT ON TABLE {ns}.gold_evaluations TO `{principal}`")
    spark.sql(f"GRANT SELECT, MODIFY ON TABLE {ns}.application_plans TO `{principal}`")
    return principal


def prepare_input(repo_root: Path, work_dir: Path, input_mode: str, reuse_geometry: bool) -> dict:
    # Exactly one shared ingestion entry point is invoked per pipeline run.
    from hawkerbridge.ingest import build_snapshot, refresh

    source_data = repo_root / "data"
    if input_mode == "archived_replay":
        archive = source_data / "raw/baseline-20260922"
        if not (archive / "provenance.json").is_file():
            raise FileNotFoundError("Archived replay requires the shipped provenance and raw files")
        shutil.copytree(source_data, work_dir, dirs_exist_ok=True)
        return build_snapshot(work_dir / "raw/baseline-20260922")
    if input_mode != "live":
        raise ValueError("input_mode must be live or archived_replay")
    if reuse_geometry:
        # Copy a checksummed cache; refresh preserves source timestamps and records reuse.
        cached = source_data / "processed/snapshot.json"
        if not cached.is_file():
            raise FileNotFoundError("Geometry reuse requested but archived snapshot is missing")
        shutil.copytree(source_data, work_dir, dirs_exist_ok=True)
    return refresh(work_dir, allow_mirror=False, reuse_geometry=reuse_geometry)


def source_rows(snapshot: dict, data_dir: Path, publication_id: str, now: datetime) -> list[dict]:
    rows = []
    for source in snapshot["manifest"]["sources"]:
        path = (data_dir / source["raw_path"]).resolve()
        if not path.is_relative_to(data_dir.resolve()):
            raise ValueError("Raw source path must stay inside the run data directory")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != source["sha256"] or len(payload) != source["bytes"]:
            raise ValueError("Raw source integrity check failed before Bronze publication")
        rows.append({"publication_id": publication_id, "source_key": source["key"],
                     "dataset_id": source["dataset_id"], "source_url": source["url"],
                     "transport_url": source["transport_url"], "source_fetched_at": source["fetched_at"],
                     "archived_reused_at": source.get("reused_at"), "mirror": bool(source.get("mirror")),
                     "sha256": source["sha256"], "byte_count": len(payload),
                     "payload_json": payload.decode("utf-8"), "ingested_at": now})
    return rows


def silver_rows(snapshot: dict, publication_id: str) -> dict[str, list[dict]]:
    def fields(items: list[dict], names: tuple[str, ...]) -> list[dict]:
        return [{"publication_id": publication_id, **{name: row.get(name) for name in names}} for row in items]

    values = {
        "silver_centres": fields(snapshot["centres"], ("id", "name", "lat", "lng", "address", "planning_area", "food_stalls", "market_stalls")),
        "silver_closures": fields(snapshot["closures"], ("id", "centre_id", "start_date", "end_date", "kind", "source_text")),
        "silver_demand_zones": fields(snapshot["demand_zones"], ("id", "name", "planning_area", "lat", "lng", "residents", "seniors", "population_year", "location_method")),
        "silver_quarantine": fields(snapshot.get("quarantine", []), ("id", "centre_id", "kind", "source_start", "source_end", "source_text", "reason")),
        "silver_food_waste": fields(snapshot.get("food_waste", []), ("year", "generated_tonnes", "recycled_tonnes", "disposed_tonnes", "recycling_rate_percent")),
        "silver_boundaries": [{"publication_id": publication_id, "id": row["properties"]["id"],
                               "planning_area": row["properties"]["planning_area"], "geometry_json": _json(row["geometry"])}
                              for row in snapshot["boundaries"]["features"]],
    }
    for row in values["silver_closures"]:
        row["start_date"], row["end_date"] = date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"])
    for row, zone in zip(values["silver_demand_zones"], snapshot["demand_zones"], strict=True):
        row["geometry_json"] = _json(zone.get("geometry"))
    for row in values["silver_food_waste"]:
        row["recycling_rate_percent"] = float(row["recycling_rate_percent"])
    return values


def engine_code_sha256() -> str:
    """Identify the imported implementation, not a manually maintained version label."""
    from hawkerbridge import engine

    return hashlib.sha256(Path(engine.__file__).read_bytes()).hexdigest()


def evaluate(snapshot: dict) -> tuple[list[dict], list[dict]]:
    """Real model results, never a fabricated accuracy score or observed impact claim."""
    from hawkerbridge.engine import PlanningEngine

    code_hash = engine_code_sha256()
    expected_hash = snapshot.get("manifest", {}).get("databricks", {}).get("engine_code_sha256")
    if expected_hash and expected_hash != code_hash:
        raise ValueError("Engine implementation changed during publication")
    engine = PlanningEngine(snapshot)
    results, analyses = [], []
    for day in EVALUATION_DATES:
        analyses.append(engine.analyse({"date": day, "radius_m": 800, "senior_weight": 2}))
        for budget in EVALUATION_BUDGETS:
            params = {"date": day, "radius_m": 800, "senior_weight": 2, "budget": budget,
                      "site_cost": 300, "meal_cost": 4, "meals_per_site": 150,
                      "max_sites": 3, "participation_rate": 0.05, "rescheduled_closure_ids": []}
            started = time.perf_counter()
            result = engine.optimise(params)
            seconds = time.perf_counter() - started
            summary, baseline = result["summary"], result["baseline"]
            if summary["spent"] > budget + 0.01 or baseline["spent"] > budget + 0.01:
                raise ValueError("Optimizer evaluation violated the scenario budget")
            if summary["weighted_benefit"] + 0.01 < baseline["weighted_benefit"]:
                raise ValueError("Published allocation is worse than its fallback baseline")
            for metric in (summary["spent"], summary["weighted_benefit"], baseline["weighted_benefit"]):
                if not math.isfinite(float(metric)):
                    raise ValueError("Non-finite optimiser metric")
            results.append({"scenario_id": f"{day}-sgd{budget}", "parameters": params,
                            "summary": summary, "baseline": baseline, "runtime_seconds": seconds,
                            "model_version": result["model_version"], "source_fingerprint": result["source_fingerprint"],
                            "engine_code_sha256": code_hash,
                            "limitations": result["limitations"]})
    return results, analyses


def run_pipeline(*, spark: Any, repo_root: Path, catalog: str, schema: str, app_name: str,
                 input_mode: str, reuse_archived_geometry: bool, experiment_id: str) -> dict:
    if input_mode not in {"live", "archived_replay"}:
        raise ValueError("Choose live or archived_replay explicitly")
    if not experiment_id:
        raise ValueError("An MLflow experiment ID is required; deploy the bundle experiment first")
    ns = bootstrap_tables(spark, catalog, schema)
    publication_id = uuid.uuid4().hex
    now = datetime.now(UTC)
    published = False

    def event(name: str, detail: str) -> None:
        append_rows(spark, ns, "pipeline_events", [{"publication_id": publication_id, "event": name,
                    "input_mode": input_mode, "detail": detail, "recorded_at": datetime.now(UTC)}])

    event("STARTED", "Single serverless task; no implicit archived-data fallback")
    try:
        grant_app_permissions(spark, ns, catalog, app_name)
        with tempfile.TemporaryDirectory(prefix="hawkerbridge-") as directory:
            work_dir = Path(directory)
            snapshot = prepare_input(repo_root, work_dir, input_mode, reuse_archived_geometry)
            append_rows(spark, ns, "bronze_sources", source_rows(snapshot, work_dir, publication_id, now))
            intermediate = silver_rows(snapshot, publication_id)
            for table, rows in intermediate.items():
                append_rows(spark, ns, table, rows)

        quality = snapshot["manifest"]["quality"]
        quality_rows = [{"publication_id": publication_id, "check_name": key, "passed": True,
                         "observed_value": float(value), "detail": "Shared ingestion validation passed; counts are observations, quarantine is retained",
                         "checked_at": now} for key, value in quality.items() if isinstance(value, (float, int))]
        import mlflow

        mlflow.set_tracking_uri("databricks")
        with mlflow.start_run(experiment_id=experiment_id, run_name=f"publication-{publication_id[:8]}") as parent:
            run_id = parent.info.run_id
            # Set metadata before engine fingerprinting; do not mutate published inputs afterward.
            code_hash = engine_code_sha256()
            snapshot["manifest"]["databricks"] = {"publication_id": publication_id, "input_mode": input_mode,
                "started_at": now.isoformat(), "mlflow_run_id": run_id,
                "engine_code_sha256": code_hash,
                "geometry_reuse_requested": reuse_archived_geometry,
                "evaluation_scope": "Declared scenarios; modelled benefit, no observed service outcomes",
                "evaluation_scenarios": len(EVALUATION_DATES) * len(EVALUATION_BUDGETS)}
            mlflow.log_params({"input_mode": input_mode, "population_year": snapshot["manifest"]["population_year"],
                               "dates": ",".join(EVALUATION_DATES), "budgets": ",".join(map(str, EVALUATION_BUDGETS)),
                               "radius_m": 800, "senior_weight": 2, "participation_rate": 0.05,
                               "comparison": "Largest demand first; identical budget and capacity",
                               "engine_code_sha256": code_hash})
            mlflow.set_tags({"project": "HawkerBridge", "publication_id": publication_id,
                             "impact_type": "scenario_only", "trained_predictor": "false"})
            mlflow.log_dict(snapshot["manifest"], "source-manifest.json")
            results, analyses = evaluate(snapshot)
            for result in results:
                summary = result["summary"]
                with mlflow.start_run(experiment_id=experiment_id, nested=True, run_name=result["scenario_id"]) as child:
                    mlflow.log_params(result["parameters"])
                    mlflow.log_metrics({"weighted_benefit": float(summary["weighted_benefit"]),
                                        "baseline_weighted_benefit": float(result["baseline"]["weighted_benefit"]),
                                        "planned_meals": float(summary["total_meals"]), "spent_sgd": float(summary["spent"]),
                                        "runtime_seconds": result["runtime_seconds"]})
                    mlflow.log_dict(result, "scenario-result.json")
                    result["mlflow_run_id"] = child.info.run_id
            mlflow.log_metrics({"scenarios_evaluated": float(len(results)), "budget_violations": 0.0,
                                "below_baseline_cases": 0.0, "quarantined_intervals": float(len(snapshot.get("quarantine", []))),
                                "mean_weighted_benefit": sum(r["summary"]["weighted_benefit"] for r in results) / len(results),
                                "mean_baseline_weighted_benefit": sum(r["baseline"]["weighted_benefit"] for r in results) / len(results)})
            mlflow.log_dict({"method": "geospatial screening + constrained allocation",
                             "engine_code_sha256": code_hash, "results": results}, "evaluation.json")
            evaluation_rows = []
            for result in results:
                s = result["summary"]
                evaluation_rows.append({"publication_id": publication_id, "scenario_id": result["scenario_id"],
                    "evaluation_date": date.fromisoformat(result["parameters"]["date"]),
                    "budget": float(s["budget"]), "spent": float(s["spent"]), "planned_meals": int(s["total_meals"]),
                    "estimated_demand": int(s["estimated_demand"]), "weighted_benefit": float(s["weighted_benefit"]),
                    "baseline_weighted_benefit": float(result["baseline"]["weighted_benefit"]),
                    "improvement_pct": float(s["improvement_pct"]), "solver_status": s["solver_status"],
                    "runtime_seconds": result["runtime_seconds"], "parameters_json": _json(result["parameters"]),
                    "result_json": _json(result), "mlflow_run_id": result["mlflow_run_id"],
                    "source_fingerprint": result["source_fingerprint"]})
            append_rows(spark, ns, "gold_evaluations", evaluation_rows)
            area_rows, zone_rows = [], []
            for analysis in analyses:
                common = {"publication_id": publication_id, "evaluation_date": date.fromisoformat(analysis["date"]),
                          "source_fingerprint": analysis["source_fingerprint"]}
                for area in analysis["area_ranking"]:
                    area_rows.append({**common, **area, "radius_m": float(analysis["radius_m"]),
                                      "coverage_pct": float(area["coverage_pct"])})
                for zone in analysis["zones"]:
                    zone_rows.append({**common, "zone_id": zone["id"], "planning_area": zone["planning_area"],
                        **{key: (float(zone[key]) if zone[key] is not None else None)
                           for key in ("baseline_distance_m", "current_distance_m", "priority_score")},
                        **{key: zone[key] for key in ("baseline_covered", "current_covered", "newly_exposed")}})
            append_rows(spark, ns, "gold_access_by_area", area_rows)
            append_rows(spark, ns, "gold_access_zones", zone_rows)
            quality_rows.extend([{"publication_id": publication_id, "check_name": name, "passed": True,
                "observed_value": 0.0, "detail": "All declared evaluation scenarios passed", "checked_at": now}
                for name in ("budget_violations", "below_baseline_cases")])
            append_rows(spark, ns, "quality_audit", quality_rows)
            edges = [("bronze_sources", table, "Shared Python ingestion; source SHA-256 checked") for table in intermediate]
            edges += [(table, "gold_evaluations", "PlanningEngine analysis and constrained optimisation")
                      for table in ("silver_centres", "silver_closures", "silver_demand_zones")]
            edges += [("gold_evaluations", "gold_snapshots", "Quality-gated publication after evaluation")]
            append_rows(spark, ns, "lineage_edges", [{"publication_id": publication_id,
                "parent_asset": f"{catalog}.{schema}.{parent_table}", "child_asset": f"{catalog}.{schema}.{child_table}",
                "transformation": method, "recorded_at": now} for parent_table, child_table, method in edges])
            mlflow.log_dict({"checks": [{k: v for k, v in row.items() if k != "checked_at"} for row in quality_rows]}, "quality-audit.json")
            create_published_views(spark, ns)
        # Final visibility boundary: failed/staged publications remain hidden from app and views.
        append_rows(spark, ns, "gold_snapshots", [{"publication_id": publication_id, "snapshot_json": _json(snapshot),
            "created_at": datetime.now(UTC), "source_fingerprint": analyses[0]["source_fingerprint"],
            "input_mode": input_mode, "mlflow_run_id": run_id}])
        published = True
        event("PUBLISHED", f"{len(results)} evaluated scenarios; app inputs are committed")
        return {"status": "PUBLISHED", "publication_id": publication_id, "input_mode": input_mode,
                "namespace": f"{catalog}.{schema}", "sources": len(snapshot["manifest"]["sources"]),
                "centres": len(snapshot["centres"]), "scenarios_evaluated": len(results), "mlflow_run_id": run_id}
    except Exception as exc:
        try:
            event("FAILED", f"{type(exc).__name__}; see restricted job logs. "
                  + ("Snapshot committed; final audit update failed." if published else "No replacement snapshot was published."))
        except Exception:
            pass
        raise
