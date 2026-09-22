"""Offline checks for the Lakeview artifact; never authenticates or calls a workspace.

See README.md for the isolated validation dependencies and CLI schema export command.
SQL runs against real archived source/evaluation rows in an in-memory DuckDB adapter;
this verifies query/field coherence, not Databricks execution or rendered layout.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import regex
import sqlglot
import yaml
from databricks.labs.lsql.lakeview import Dashboard
from jsonschema import Draft202012Validator, ValidationError, validators
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = Path(__file__).with_name("hawkerbridge-evidence.lvdash.json")
VIEWS = {
    "published_closure_calendar",
    "published_evaluations",
    "published_bronze_sources",
    "published_quarantine",
    "published_centres",
}


def load_real_rows(db):
    """Materialise only the real input columns queried by this dashboard."""
    snapshot = json.loads((ROOT / "data/processed/snapshot.json").read_text())
    evaluation = json.loads((ROOT / "data/processed/evaluation.json").read_text())
    day = "2026-09-28"
    closed = {
        c["centre_id"] for c in snapshot["closures"] if c["start_date"] <= day <= c["end_date"]
    }
    stalls = sum(c["food_stalls"] for c in snapshot["centres"] if c["id"] in closed)
    db.execute(
        "CREATE TABLE published_closure_calendar (closure_date DATE, closed_centres BIGINT, food_stalls_closed BIGINT)"
    )
    db.execute(
        "INSERT INTO published_closure_calendar VALUES (?, ?, ?)", [day, len(closed), stalls]
    )
    db.execute("CREATE TABLE published_centres (id VARCHAR, name VARCHAR)")
    db.executemany(
        "INSERT INTO published_centres VALUES (?, ?)",
        [(c["id"], c["name"]) for c in snapshot["centres"]],
    )
    db.execute(
        "CREATE TABLE published_quarantine (centre_id VARCHAR, kind VARCHAR, source_start VARCHAR, source_end VARCHAR, reason VARCHAR, source_text VARCHAR)"
    )
    db.executemany(
        "INSERT INTO published_quarantine VALUES (?, ?, ?, ?, ?, ?)",
        [
            tuple(
                row.get(key)
                for key in (
                    "centre_id",
                    "kind",
                    "source_start",
                    "source_end",
                    "reason",
                    "source_text",
                )
            )
            for row in snapshot["quarantine"]
        ],
    )
    db.execute(
        "CREATE TABLE published_bronze_sources (source_key VARCHAR, source_fetched_at VARCHAR, archived_reused_at VARCHAR, mirror BOOLEAN, sha256 VARCHAR, source_url VARCHAR)"
    )
    db.executemany(
        "INSERT INTO published_bronze_sources VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                row["key"],
                row["fetched_at"],
                row.get("reused_at"),
                bool(row.get("mirror")),
                row["sha256"],
                row["url"],
            )
            for row in snapshot["manifest"]["sources"]
        ],
    )
    db.execute(
        "CREATE TABLE published_evaluations (evaluation_date DATE, budget DOUBLE, weighted_benefit DOUBLE, baseline_weighted_benefit DOUBLE)"
    )
    scenarios = [s for s in evaluation["scenarios"] if s["parameters"]["radius_m"] == 800]
    db.executemany(
        "INSERT INTO published_evaluations VALUES (?, ?, ?, ?)",
        [
            (
                s["parameters"]["date"],
                s["parameters"]["budget"],
                s["summary"]["weighted_benefit"],
                s["baseline"]["weighted_benefit"],
            )
            for s in scenarios
        ],
    )
    return snapshot, len(closed)


def validate_bundle_schema(path):
    schema = json.loads(path.read_text())
    resource = yaml.safe_load((ROOT / "resources/dashboard.yml").read_text())
    instance = resource["resources"]["dashboards"]["hawkerbridge_evidence"]

    # CLI JSON Schema uses Go Unicode regex classes, so use the compatible regex
    # engine for pattern checks instead of Python's narrower re implementation.
    def pattern(validator, value, instance, schema):
        if isinstance(instance, str) and not regex.search(value, instance):
            yield ValidationError(f"{instance!r} does not match {value!r}")

    validator = validators.extend(Draft202012Validator, {"pattern": pattern})
    target = {
        "$defs": schema["$defs"],
        "$ref": "#/$defs/github.com/databricks/cli/bundle/config/resources.Dashboard",
    }
    validator(target).validate(instance)
    assert instance["dataset_catalog"] == "${var.catalog}"
    assert instance["dataset_schema"] == "${var.schema}"
    assert instance["warehouse_id"] == "${var.warehouse_id}"
    assert instance["embed_credentials"] is False and not instance.get("permissions")
    assert (ROOT / "resources" / instance["file_path"]).resolve() == DASHBOARD_PATH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-schema", type=Path, required=True)
    args = parser.parse_args()
    body = json.loads(DASHBOARD_PATH.read_text())
    assert Dashboard.from_dict(body).as_dict() == body, "Unsupported or lossy Lakeview fields"
    validate_bundle_schema(args.bundle_schema)
    datasets = {dataset["name"]: dataset for dataset in body["datasets"]}
    assert len(datasets) == len(body["datasets"]) == 4
    fields_by_dataset, rows_by_dataset = {}, {}
    with duckdb.connect() as db:
        snapshot, closure_count = load_real_rows(db)
        for name, dataset in datasets.items():
            statements = sqlglot.parse(dataset["query"], read="databricks")
            assert len(statements) == 1 and isinstance(statements[0], (exp.Select, exp.Union))
            for table in statements[0].find_all(exp.Table):
                assert table.name in VIEWS and not table.db and not table.catalog
            result = db.execute(statements[0].sql(dialect="duckdb"))
            fields_by_dataset[name] = {column[0] for column in result.description}
            rows_by_dataset[name] = result.fetchall()
    assert rows_by_dataset["closures_on_demo_date"][0][1] == closure_count
    assert len(rows_by_dataset["published_source_provenance"]) == len(
        snapshot["manifest"]["sources"]
    )
    assert len(rows_by_dataset["unresolved_interval_review"]) == len(snapshot["quarantine"])
    comparison = rows_by_dataset["evaluated_budget_comparison"]
    assert len(comparison) == 6
    for budget in {row[0] for row in comparison}:
        values = {row[1]: row[2] for row in comparison if row[0] == budget}
        assert values["Optimised proposal"] >= values["Largest-demand-first baseline"]
    layouts = [item for page in body["pages"] for item in page["layout"]]
    assert len(layouts) == 4
    occupied = set()
    for item in layouts:
        position, widget = item["position"], item["widget"]
        assert (
            position["width"] > 0
            and position["height"] > 0
            and position["x"] >= 0
            and position["y"] >= 0
        )
        assert position["x"] + position["width"] <= 6
        cells = {
            (x, y)
            for x in range(position["x"], position["x"] + position["width"])
            for y in range(position["y"], position["y"] + position["height"])
        }
        assert not occupied.intersection(cells), "Overlapping widgets"
        occupied.update(cells)
        projected = set()
        for query in widget["queries"]:
            source = query["query"]["datasetName"]
            for field in query["query"]["fields"]:
                assert field["name"] in fields_by_dataset[source]
                assert field["expression"] == f"`{field['name']}`"
                projected.add(field["name"])
        encodings = widget["spec"]["encodings"]
        references = encodings.get("columns", []) + [
            value for value in encodings.values() if isinstance(value, dict)
        ]
        assert all(ref["fieldName"] in projected for ref in references if "fieldName" in ref)
    print(
        json.dumps(
            {
                "status": "offline_checks_passed",
                "widgets": len(layouts),
                "query_row_counts": {k: len(v) for k, v in rows_by_dataset.items()},
                "closure_count_from_archive": closure_count,
                "workspace_executed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
