"""Meaningful workspace boundary tests with SDK-shaped responses; no workspace needed."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from hawkerbridge.databricks_store import DatabricksStore, DatabricksStoreError


def response(rows=None, *, state="SUCCEEDED", names=None, **manifest):
    result = {"chunk_index": 0, "row_offset": 0, "data_array": rows or []}
    return {
        "statement_id": "statement-123", "status": {"state": state}, "result": result,
        "manifest": {"schema": {"columns": [{"name": name} for name in (names or [])]},
                     "total_row_count": len(rows or []), **manifest},
    }


@pytest.fixture
def setup_store():
    client = Mock()
    config = SimpleNamespace(databricks_warehouse_id="abc123", catalog="workspace", schema="hawkerbridge")
    store = DatabricksStore(config, client=client, poll_interval_seconds=0)
    return store, client.statement_execution


def test_missing_config_and_identifier_injection_are_rejected():
    for warehouse, catalog, schema in [("", "workspace", "hawkerbridge"),
                                       ("a", "workspace; DROP TABLE plans", "hawkerbridge"),
                                       ("a", "workspace", "bad.schema")]:
        with pytest.raises(ValueError):
            DatabricksStore(SimpleNamespace(databricks_warehouse_id=warehouse,
                                          catalog=catalog, schema=schema), client=Mock())


def test_pending_statement_is_polled_before_success(setup_store):
    store, api = setup_store
    api.execute_statement.return_value = response(state="PENDING")
    api.get_statement.side_effect = [response(state="RUNNING"), response([["ok"]], names=["answer"])]
    assert store._execute("SELECT 'ok' AS answer") == [{"answer": "ok"}]
    assert api.get_statement.call_count == 2


def test_timeout_requests_cancellation_and_never_returns_success(setup_store, monkeypatch):
    store, api = setup_store
    api.execute_statement.return_value = response(state="RUNNING")
    monkeypatch.setattr("hawkerbridge.databricks_store.time.monotonic", Mock(side_effect=[0, 61]))
    with pytest.raises(DatabricksStoreError, match="timed out"):
        store._execute("SELECT 1")
    api.cancel_execution.assert_called_once_with(statement_id="statement-123")


@pytest.mark.parametrize("state", ["FAILED", "CANCELED", "CLOSED", None])
def test_failed_or_unknown_state_fails_closed(setup_store, state):
    store, api = setup_store
    api.execute_statement.return_value = response(state=state)
    with pytest.raises(DatabricksStoreError, match="did not succeed"):
        store._execute("SELECT 1")


def test_chunks_are_fetched_via_sdk_and_nulls_preserved(setup_store):
    store, api = setup_store
    initial = response([["one"]], names=["answer"], total_row_count=2)
    initial["result"]["next_chunk_index"] = 1
    api.execute_statement.return_value = initial
    api.get_statement_result_chunk_n.return_value = {
        "chunk_index": 1, "row_offset": 1, "data_array": [[None]],
    }
    assert store._execute("SELECT answer FROM example") == [{"answer": "one"}, {"answer": None}]
    api.get_statement_result_chunk_n.assert_called_once_with(statement_id="statement-123", chunk_index=1)


@pytest.mark.parametrize("problem", ["truncated", "missing_chunk", "loop", "bad_offset", "external_links"])
def test_incomplete_or_unsafe_results_are_rejected(setup_store, problem):
    store, api = setup_store
    value = response([["x"]], names=["answer"])
    if problem == "truncated":
        value["manifest"]["truncated"] = True
    elif problem == "missing_chunk":
        value["manifest"]["total_row_count"] = 2
    elif problem == "loop":
        value["result"]["next_chunk_index"] = 0
    elif problem == "bad_offset":
        value["result"]["row_offset"] = 7
    else:
        value["result"]["external_links"] = [{"external_link": "https://invalid.example/secret"}]
    api.execute_statement.return_value = value
    with pytest.raises(DatabricksStoreError):
        store._execute("SELECT answer FROM example")


def test_owner_and_plan_payload_use_parameters_even_with_quotes(setup_store):
    store, api = setup_store
    api.execute_statement.return_value = response()
    owner = "user' OR 1=1 --"
    plan = {"id": "plan'1", "updated_at": "2026-09-22T12:00:00Z", "notes": "a'); DROP TABLE x; --"}
    store.save_plan(owner, plan)
    args = api.execute_statement.call_args.kwargs
    assert owner not in args["statement"] and plan["notes"] not in args["statement"]
    assert "target.owner_id = source.owner_id AND target.plan_id = source.plan_id" in args["statement"]
    parameters = {p.name: p.value for p in args["parameters"]}
    assert parameters["owner_id"] == owner
    assert json.loads(parameters["plan_json"]) == plan


def test_reads_and_deletes_remain_owner_scoped(setup_store):
    store, api = setup_store
    api.execute_statement.return_value = response([], names=["plan_json"])
    assert store.get_plan("bob", "alice-plan") is None
    assert store.delete_plan("bob", "alice-plan") is False
    assert store.list_plans("bob") == []
    for call in api.execute_statement.call_args_list:
        assert "WHERE owner_id = :owner_id" in call.kwargs["statement"]
        assert next(p.value for p in call.kwargs["parameters"] if p.name == "owner_id") == "bob"
    assert all(not c.kwargs["statement"].startswith("DELETE") for c in api.execute_statement.call_args_list)


def test_delete_returns_actual_affected_count_when_available(setup_store):
    store, api = setup_store
    api.execute_statement.side_effect = [response([[json.dumps({"id": "p"})]], names=["plan_json"]),
                                         response([["1"]], names=["num_affected_rows"])]
    assert store.delete_plan("owner", "p") is True
    assert "AND plan_id = :plan_id" in api.execute_statement.call_args.kwargs["statement"]


def test_snapshot_cannot_silently_fall_back_to_local_data(setup_store):
    store, api = setup_store
    api.execute_statement.return_value = response([], names=["snapshot_json"])
    with pytest.raises(DatabricksStoreError, match="run hawkerbridge_pipeline"):
        store.load_snapshot()
    api.execute_statement.return_value = response([["not json"]], names=["snapshot_json"])
    with pytest.raises(DatabricksStoreError, match="Invalid snapshot"):
        store.load_snapshot()
    snapshot = {"manifest": {}, "centres": [], "closures": [], "demand_zones": []}
    api.execute_statement.return_value = response([[json.dumps(snapshot)]], names=["snapshot_json"])
    assert store.load_snapshot() == snapshot


@pytest.fixture(scope="module")
def pipeline_module():
    """Load the standalone job module without shadowing the databricks SDK package."""
    import importlib.util
    from pathlib import Path

    file_path = Path(__file__).resolve().parents[1] / "databricks/pipeline.py"
    spec = importlib.util.spec_from_file_location("hawkerbridge_pipeline_test", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pipeline_archive_integrity_and_structured_rows(pipeline_module, tmp_path):
    from datetime import date, datetime
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    snapshot = pipeline_module.prepare_input(root, tmp_path, "archived_replay", True)
    rows = pipeline_module.source_rows(snapshot, tmp_path, "publication-test", datetime.now())
    assert len(rows) == 5
    assert all(row["sha256"] and row["payload_json"] for row in rows)
    silver = pipeline_module.silver_rows(snapshot, "publication-test")
    assert len(silver["silver_centres"]) >= 100
    assert len(silver["silver_demand_zones"]) == 332
    assert all(isinstance(row["start_date"], date) for row in silver["silver_closures"])
    source = snapshot["manifest"]["sources"][0]
    (tmp_path / source["raw_path"]).write_text("corrupted")
    with pytest.raises(ValueError, match="integrity"):
        pipeline_module.source_rows(snapshot, tmp_path, "publication-test", datetime.now())


def test_pipeline_live_error_never_becomes_archived_replay(pipeline_module, tmp_path, monkeypatch):
    from pathlib import Path

    refresh = Mock(side_effect=ConnectionError("network is restricted"))
    replay = Mock()
    monkeypatch.setattr("hawkerbridge.ingest.refresh", refresh)
    monkeypatch.setattr("hawkerbridge.ingest.build_snapshot", replay)
    with pytest.raises(ConnectionError, match="restricted"):
        pipeline_module.prepare_input(Path(__file__).resolve().parents[1], tmp_path, "live", False)
    refresh.assert_called_once_with(tmp_path, allow_mirror=False, reuse_geometry=False)
    replay.assert_not_called()


@pytest.fixture
def fake_mlflow(monkeypatch):
    import sys
    from contextlib import contextmanager

    module = Mock()
    counter = 0

    @contextmanager
    def start_run(**kwargs):
        nonlocal counter
        counter += 1
        yield SimpleNamespace(info=SimpleNamespace(run_id=f"run-{counter}"))

    module.start_run = start_run
    monkeypatch.setitem(sys.modules, "mlflow", module)
    return module


def test_pipeline_publishes_last_and_records_real_evaluation(pipeline_module, fake_mlflow, monkeypatch):
    from datetime import date, datetime
    from pathlib import Path

    # A strict small Spark adapter catches driver schema errors without pretending to
    # execute Delta operations or to verify a Databricks workspace.
    written = []

    class Frame:
        def __init__(self, rows):
            self.rows = rows
            self.write = self

        def format(self, _):
            return self

        def mode(self, _):
            return self

        def saveAsTable(self, table):
            written.append((table, self.rows))

    class Spark:
        def sql(self, statement):
            return None

        def createDataFrame(self, rows, schema):
            for field in schema.split(", "):
                name, kind = field.split()
                expected = {"STRING": str, "BIGINT": int, "INT": int, "DOUBLE": float,
                            "BOOLEAN": bool, "TIMESTAMP": datetime, "DATE": date}[kind]
                for row in rows:
                    assert name in row, (name, row)
                    assert row[name] is None or isinstance(row[name], expected), (name, row[name], expected)
            return Frame(rows)

    monkeypatch.setattr(pipeline_module, "grant_app_permissions", lambda *args: "principal-test")
    result = pipeline_module.run_pipeline(spark=Spark(), repo_root=Path(__file__).resolve().parents[1],
        catalog="workspace", schema="hawkerbridge", app_name="hawkerbridge", input_mode="archived_replay",
        reuse_archived_geometry=True, experiment_id="experiment-test")
    assert result["status"] == "PUBLISHED" and result["scenarios_evaluated"] == 9
    tables = [table.split(".")[-1] for table, _ in written]
    assert tables[-2:] == ["gold_snapshots", "pipeline_events"]
    snapshots = next(rows for table, rows in written if table.endswith(".gold_snapshots"))
    published = json.loads(snapshots[0]["snapshot_json"])
    assert published["manifest"]["databricks"]["input_mode"] == "archived_replay"
    from hawkerbridge.engine import PlanningEngine
    assert snapshots[0]["source_fingerprint"] == PlanningEngine(published).fingerprint
    evaluations = next(rows for table, rows in written if table.endswith(".gold_evaluations"))
    assert len(evaluations) == 9
    assert all(row["spent"] <= row["budget"] for row in evaluations)
    assert all(row["weighted_benefit"] + .01 >= row["baseline_weighted_benefit"] for row in evaluations)
    code_hash = pipeline_module.engine_code_sha256()
    assert published["manifest"]["databricks"]["engine_code_sha256"] == code_hash
    assert all(json.loads(row["result_json"])["engine_code_sha256"] == code_hash for row in evaluations)
    assert any(call.args[0].get("engine_code_sha256") == code_hash
               for call in fake_mlflow.log_params.call_args_list)
    fake_mlflow.log_metrics.assert_called()


def test_pipeline_failure_does_not_publish_snapshot(pipeline_module, fake_mlflow, monkeypatch):
    from pathlib import Path

    written = []
    monkeypatch.setattr(pipeline_module, "bootstrap_tables", lambda *args: "`workspace`.`hawkerbridge`")
    monkeypatch.setattr(pipeline_module, "grant_app_permissions", lambda *args: "principal-test")
    monkeypatch.setattr(pipeline_module, "append_rows", lambda spark, ns, table, rows: written.append((table, rows)))
    monkeypatch.setattr(pipeline_module, "evaluate", Mock(side_effect=ValueError("evaluation failed")))
    with pytest.raises(ValueError, match="evaluation failed"):
        pipeline_module.run_pipeline(spark=Mock(), repo_root=Path(__file__).resolve().parents[1],
            catalog="workspace", schema="hawkerbridge", app_name="hawkerbridge", input_mode="archived_replay",
            reuse_archived_geometry=True, experiment_id="experiment-test")
    assert all(table != "gold_snapshots" for table, _ in written)
    assert written[-1][1][0]["event"] == "FAILED"


def test_pipeline_rejects_engine_changes_after_manifest_versioning(pipeline_module):
    with pytest.raises(ValueError, match="changed during publication"):
        pipeline_module.evaluate({"manifest": {"databricks": {"engine_code_sha256": "0" * 64}}})


def test_plan_list_projects_summary_without_loading_large_result_blobs(setup_store):
    store, api = setup_store
    api.execute_statement.return_value = response(
        [["p1", "Draft", '{"date":"2026-09-22"}', '{"total_meals":150}']],
        names=["id", "title", "parameters_json", "summary_json"],
    )
    plans = store.list_plans("owner")
    assert plans[0]["result"] == {"summary": {"total_meals": 150}}
    assert plans[0]["parameters"] == {"date": "2026-09-22"}
    assert "SELECT plan_json" not in api.execute_statement.call_args.kwargs["statement"]


def test_cloud_evaluation_requires_matching_snapshot_and_complete_results(setup_store):
    store, api = setup_store
    names = ["result_json", "source_fingerprint", "snapshot_fingerprint", "publication_id",
             "created_at", "input_mode", "expected_scenarios", "expected_engine_hash"]
    code_hash = "a" * 64
    result = {"scenario_id": "one", "source_fingerprint": "fingerprint", "engine_code_sha256": code_hash}
    row = [json.dumps(result), "fingerprint", "fingerprint", "pub1", "2026-09-22", "live", "1", code_hash]
    api.execute_statement.return_value = response([row], names=names)
    value = store.load_evaluation("fingerprint")
    assert value["scenarios_evaluated"] == 1 and value["input_mode"] == "live"
    assert value["engine_code_sha256"] == code_hash
    assert "WHERE source_fingerprint = :source_fingerprint" in api.execute_statement.call_args.kwargs["statement"]
    row[2] = "different"
    api.execute_statement.return_value = response([row], names=names)
    with pytest.raises(DatabricksStoreError, match="fingerprint"):
        store.load_evaluation("fingerprint")
    row[2], row[6] = "fingerprint", "2"
    with pytest.raises(DatabricksStoreError, match="incomplete"):
        store.load_evaluation("fingerprint")
    api.execute_statement.return_value = response([], names=names)
    with pytest.raises(DatabricksStoreError, match="No cloud evaluation"):
        store.load_evaluation("fingerprint")


@pytest.mark.parametrize("problem", ["missing_manifest_hash", "missing_result_hash", "mixed_code", "wrong_input"])
def test_cloud_evaluation_rejects_unversioned_or_mixed_implementations(setup_store, problem):
    store, api = setup_store
    code_hash = "a" * 64
    names = ["result_json", "source_fingerprint", "snapshot_fingerprint", "publication_id",
             "created_at", "input_mode", "expected_scenarios", "expected_engine_hash"]
    results = [{"scenario_id": f"scenario-{i}", "source_fingerprint": "fp", "engine_code_sha256": code_hash}
               for i in range(2)]
    expected = code_hash
    if problem == "missing_manifest_hash":
        expected = None
    elif problem == "missing_result_hash":
        results[1].pop("engine_code_sha256")
    elif problem == "mixed_code":
        results[1]["engine_code_sha256"] = "b" * 64
    else:
        results[1]["source_fingerprint"] = "other-input"
    rows = [[json.dumps(result), "fp", "fp", "pub1", "2026-09-22", "live", "2", expected]
            for result in results]
    api.execute_statement.return_value = response(rows, names=names)
    with pytest.raises(DatabricksStoreError, match="fingerprint"):
        store.load_evaluation("fp")


def test_dashboard_cooked_food_density_excludes_zero_food_markets():
    """Execute the real portable query with synthetic and archived source data."""
    import sqlite3
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sql = (root / "databricks/sql/dashboard_queries.sql").read_text()
    query = sql.split("-- 7.", 1)[1].split("WITH populations AS", 1)[1].split("-- 8.", 1)[0]
    query = "WITH populations AS" + query
    snapshot = json.loads((root / "data/processed/snapshot.json").read_text())
    with sqlite3.connect(":memory:") as database:
        database.row_factory = sqlite3.Row
        database.execute("CREATE TABLE published_centres (planning_area TEXT, food_stalls INTEGER)")
        database.execute("CREATE TABLE published_demand_zones (planning_area TEXT, residents INTEGER, seniors INTEGER)")
        database.executemany("INSERT INTO published_centres VALUES (?, ?)",
                             [(c["planning_area"], c["food_stalls"]) for c in snapshot["centres"]])
        database.executemany("INSERT INTO published_demand_zones VALUES (?, ?, ?)",
                             [(z["planning_area"], z["residents"], z["seniors"]) for z in snapshot["demand_zones"]])
        rows = database.execute(query).fetchall()
        assert sum(row["food_centres"] for row in rows) == 120
        assert sum(row["inventory_centres"] for row in rows) == 123
        database.execute("INSERT INTO published_centres VALUES ('Test area', 0)")
        database.execute("INSERT INTO published_demand_zones VALUES ('Test area', 10000, 1000)")
        row = next(row for row in database.execute(query) if row["planning_area"] == "Test area")
        assert row["inventory_centres"] == 1
        assert row["food_centres"] == 0 and row["food_centres_per_10000_residents"] == 0
