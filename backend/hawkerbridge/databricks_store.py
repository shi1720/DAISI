"""Owner-scoped Delta persistence through the Databricks Statement Execution API.

App authentication belongs to the API layer. Callers must derive owner_id from the
trusted platform identity, never a request payload. This store uses the app's SDK
automatic credentials; it never falls back to local data or accepts SQL identifiers
from requests. Unity Catalog permissions are provisioned before the app starts.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    Disposition,
    ExecuteStatementRequestOnWaitTimeout,
    Format,
    StatementParameterListItem,
)

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")


class DatabricksStoreError(RuntimeError):
    """Workspace storage is unavailable or returned incomplete/untrusted results."""


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def _state(response: Any) -> str | None:
    state = _get(_get(response, "status"), "state")
    return getattr(state, "value", state)


def _identity(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError(f"A non-empty {label} is required")
    return value


class DatabricksStore:
    """Bounded SQL execution with parameter markers and complete chunk retrieval."""

    def __init__(
        self,
        config: Any,
        *,
        client: Any = None,
        timeout_seconds: float = 60.0,
        poll_interval_seconds: float = 0.5,
    ) -> None:
        warehouse = getattr(config, "databricks_warehouse_id", None)
        catalog = getattr(config, "catalog", None)
        schema = getattr(config, "schema", None)
        if not isinstance(warehouse, str) or not warehouse.strip():
            raise ValueError("DATABRICKS_WAREHOUSE_ID must be configured for Databricks storage")
        if any(not isinstance(value, str) or not _IDENTIFIER.fullmatch(value)
               for value in (catalog, schema)):
            raise ValueError("HAWKERBRIDGE_CATALOG and HAWKERBRIDGE_SCHEMA must be simple SQL identifiers")
        if timeout_seconds <= 0 or poll_interval_seconds < 0:
            raise ValueError("SQL timeout must be positive and poll interval non-negative")
        self.warehouse_id = warehouse
        self.namespace = f"`{catalog}`.`{schema}`"
        self.client = client if client is not None else WorkspaceClient()
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def _execute(self, statement: str, parameters: dict[str, str] | None = None) -> list[dict]:
        api = self.client.statement_execution
        started = time.monotonic()
        response = api.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=statement,
            parameters=[StatementParameterListItem(name=name, value=value, type="STRING")
                        for name, value in (parameters or {}).items()],
            wait_timeout="0s",
            on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
            disposition=Disposition.INLINE,
            format=Format.JSON_ARRAY,
            byte_limit=20 * 1024 * 1024,
        )
        statement_id = _get(response, "statement_id")
        while _state(response) in {"PENDING", "RUNNING"}:
            if not statement_id:
                raise DatabricksStoreError("Databricks returned a running statement without an ID")
            remaining = self.timeout_seconds - (time.monotonic() - started)
            if remaining <= 0:
                try:
                    api.cancel_execution(statement_id=statement_id)
                except Exception:
                    # Cancellation is best effort, but timeout is never reported as success.
                    pass
                raise DatabricksStoreError("Databricks SQL timed out; retry after checking the warehouse")
            time.sleep(min(self.poll_interval_seconds, remaining))
            response = api.get_statement(statement_id=statement_id)
        state = _state(response)
        if state != "SUCCEEDED":
            # Do not return the SQL text, parameter values or raw server exception to a browser.
            raise DatabricksStoreError(f"Databricks statement did not succeed ({state or 'missing status'})")
        manifest = _get(response, "manifest")
        if _get(manifest, "truncated", False):
            raise DatabricksStoreError("Databricks result was truncated; refusing partial data")
        columns = _get(_get(manifest, "schema"), "columns", []) or []
        names = [_get(column, "name") for column in columns]
        if len(names) != len(set(names)) or any(not isinstance(name, str) for name in names):
            raise DatabricksStoreError("Databricks result has an invalid column schema")
        rows: list[dict] = []
        chunk = _get(response, "result")
        visited: set[int] = set()
        while chunk is not None:
            if _get(chunk, "external_links"):
                raise DatabricksStoreError("Unexpected external result links in INLINE response")
            index = _get(chunk, "chunk_index", 0)
            if index is None:
                index = 0
            if not isinstance(index, int) or index < 0 or index in visited or len(visited) >= 1024:
                raise DatabricksStoreError("Invalid or repeated Databricks result chunk")
            visited.add(index)
            offset = _get(chunk, "row_offset")
            if offset is not None and offset != len(rows):
                raise DatabricksStoreError("Databricks result chunks have inconsistent offsets")
            data = _get(chunk, "data_array", []) or []
            for row in data:
                if not isinstance(row, (list, tuple)) or len(row) != len(names):
                    raise DatabricksStoreError("Databricks result row does not match its schema")
                rows.append(dict(zip(names, row, strict=True)))
                if len(rows) > 10000:
                    raise DatabricksStoreError("Databricks result exceeded the application row limit")
            next_index = _get(chunk, "next_chunk_index")
            if next_index is None:
                break
            if not statement_id or not isinstance(next_index, int) or next_index <= index:
                raise DatabricksStoreError("Invalid Databricks continuation chunk")
            if time.monotonic() - started >= self.timeout_seconds:
                raise DatabricksStoreError("Databricks result retrieval timed out")
            chunk = api.get_statement_result_chunk_n(
                statement_id=statement_id, chunk_index=next_index
            )
        expected = _get(manifest, "total_row_count")
        if expected is not None and expected != len(rows):
            raise DatabricksStoreError("Databricks returned an incomplete result")
        return rows

    @staticmethod
    def _json_object(value: Any, label: str) -> dict:
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise DatabricksStoreError(f"Invalid {label} JSON in Databricks storage") from exc
        if not isinstance(parsed, dict):
            raise DatabricksStoreError(f"Invalid {label} object in Databricks storage")
        return parsed

    def load_snapshot(self) -> dict:
        rows = self._execute(
            f"SELECT snapshot_json FROM {self.namespace}.gold_snapshots "
            "ORDER BY created_at DESC, publication_id DESC LIMIT 1"
        )
        if not rows:
            raise DatabricksStoreError("No published Databricks snapshot; run hawkerbridge_pipeline first")
        snapshot = self._json_object(rows[0].get("snapshot_json"), "snapshot")
        if not all(key in snapshot for key in ("manifest", "centres", "closures", "demand_zones")):
            raise DatabricksStoreError("Published Databricks snapshot is missing required fields")
        return snapshot

    def list_plans(self, owner_id: str) -> list[dict]:
        # Project metadata in SQL; returning every embedded map/result for 200 plans
        # would waste quota and exceed the INLINE result limit.
        names = ("id", "title", "status", "created_at", "updated_at", "date", "notes",
                 "reviewed_at", "reviewed_by")
        projection = ", ".join(f"get_json_object(plan_json, '$.{name}') AS `{name}`" for name in names)
        rows = self._execute(
            f"SELECT {projection}, get_json_object(plan_json, '$.parameters') AS parameters_json, "
            f"get_json_object(plan_json, '$.result.summary') AS summary_json FROM {self.namespace}.application_plans "
            "WHERE owner_id = :owner_id ORDER BY updated_at DESC, plan_id",
            {"owner_id": _identity(owner_id, "owner")},
        )
        return [{**{name: row.get(name) for name in names if row.get(name) is not None},
                 "parameters": self._json_object(row.get("parameters_json"), "plan parameters"),
                 "result": {"summary": self._json_object(row.get("summary_json"), "plan summary")}}
                for row in rows]

    def load_evaluation(self, source_fingerprint: str | None = None) -> dict:
        """Retrieve actual cloud evaluation for the app's loaded snapshot version.

        Passing the engine fingerprint avoids pairing a running app's older inputs
        with a newer pipeline publication. No baked local evaluation is substituted.
        """
        where, parameters = "", {}
        if source_fingerprint is not None:
            where = "WHERE source_fingerprint = :source_fingerprint"
            parameters = {"source_fingerprint": _identity(source_fingerprint, "source fingerprint")}
        rows = self._execute(
            "WITH chosen AS (SELECT publication_id, source_fingerprint, created_at, input_mode, "
            "get_json_object(snapshot_json, '$.manifest.databricks.evaluation_scenarios') AS expected_scenarios, "
            "get_json_object(snapshot_json, '$.manifest.databricks.engine_code_sha256') AS expected_engine_hash "
            f"FROM {self.namespace}.gold_snapshots {where} "
            "ORDER BY created_at DESC, publication_id DESC LIMIT 1) "
            "SELECT e.result_json, e.source_fingerprint, p.source_fingerprint AS snapshot_fingerprint, "
            "p.publication_id, p.created_at, p.input_mode, p.expected_scenarios, p.expected_engine_hash "
            f"FROM {self.namespace}.gold_evaluations e JOIN chosen p ON e.publication_id = p.publication_id "
            "ORDER BY e.evaluation_date, e.budget", parameters,
        )
        if not rows:
            raise DatabricksStoreError("No cloud evaluation exists for this published snapshot")
        fingerprint = rows[0]["snapshot_fingerprint"]
        if any(row["source_fingerprint"] != fingerprint for row in rows):
            raise DatabricksStoreError("Cloud evaluation fingerprint does not match its snapshot")
        expected = rows[0].get("expected_scenarios")
        if expected is None or int(expected) != len(rows):
            raise DatabricksStoreError("Cloud evaluation has incomplete scenario results")
        results = [self._json_object(row.get("result_json"), "evaluation") for row in rows]
        code_hash = rows[0].get("expected_engine_hash")
        if not isinstance(code_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", code_hash):
            raise DatabricksStoreError("Cloud evaluation has no valid engine code fingerprint")
        if any(row.get("expected_engine_hash") != code_hash for row in rows) or any(
            result.get("engine_code_sha256") != code_hash for result in results
        ):
            raise DatabricksStoreError("Cloud evaluation engine code fingerprints are inconsistent")
        if any(result.get("source_fingerprint") != fingerprint for result in results):
            raise DatabricksStoreError("Cloud evaluation result fingerprint does not match its snapshot")
        return {"method": "Predeclared geospatial allocation scenarios versus largest-demand-first baseline",
                "source_fingerprint": fingerprint, "publication_id": rows[0]["publication_id"],
                "engine_code_sha256": code_hash,
                "generated_at": rows[0]["created_at"], "input_mode": rows[0]["input_mode"],
                "scenarios_evaluated": len(results), "results": results,
                "scope": "Modelled objectives under stated assumptions, not observed demand or social impact"}

    def get_plan(self, owner_id: str, plan_id: str) -> dict | None:
        rows = self._execute(
            f"SELECT plan_json FROM {self.namespace}.application_plans "
            "WHERE owner_id = :owner_id AND plan_id = :plan_id LIMIT 1",
            {"owner_id": _identity(owner_id, "owner"), "plan_id": _identity(plan_id, "plan ID")},
        )
        return self._json_object(rows[0].get("plan_json"), "plan") if rows else None

    def save_plan(self, owner_id: str, plan: dict) -> None:
        owner_id = _identity(owner_id, "owner")
        plan_id = _identity(plan.get("id"), "plan ID")
        updated_at = _identity(plan.get("updated_at"), "update timestamp")
        plan_json = json.dumps(plan, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        self._execute(
            f"MERGE INTO {self.namespace}.application_plans AS target "
            "USING (SELECT :owner_id AS owner_id, :plan_id AS plan_id, :plan_json AS plan_json, "
            "CAST(:updated_at AS TIMESTAMP) AS updated_at) AS source "
            "ON target.owner_id = source.owner_id AND target.plan_id = source.plan_id "
            "WHEN MATCHED THEN UPDATE SET plan_json = source.plan_json, updated_at = source.updated_at "
            "WHEN NOT MATCHED THEN INSERT (owner_id, plan_id, plan_json, updated_at) "
            "VALUES (source.owner_id, source.plan_id, source.plan_json, source.updated_at)",
            {"owner_id": owner_id, "plan_id": plan_id, "plan_json": plan_json, "updated_at": updated_at},
        )

    def delete_plan(self, owner_id: str, plan_id: str) -> bool:
        # The preliminary owner-scoped lookup also works on warehouses whose DELETE
        # response does not contain a num_affected_rows result set.
        if self.get_plan(owner_id, plan_id) is None:
            return False
        rows = self._execute(
            f"DELETE FROM {self.namespace}.application_plans "
            "WHERE owner_id = :owner_id AND plan_id = :plan_id",
            {"owner_id": _identity(owner_id, "owner"), "plan_id": _identity(plan_id, "plan ID")},
        )
        if rows and "num_affected_rows" in rows[0]:
            return int(rows[0]["num_affected_rows"] or 0) > 0
        return True
