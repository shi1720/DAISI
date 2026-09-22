# Databricks notebook source
# MAGIC %md
# MAGIC # HawkerBridge · one source-to-decision run
# MAGIC This notebook uses the same ingestion and planning code as the application.
# MAGIC A published snapshot is committed only after data checks and measured optimiser
# MAGIC evaluation succeed. `archived_replay` is explicitly labelled and never an
# MAGIC automatic replacement for a failed live refresh. No personal beneficiary data.

# COMMAND ----------

import json
import sys
from pathlib import Path

# Job parameters are automatically exposed as widgets by Lakeflow Jobs.
for name, default in {
    "repo_root": "", "catalog": "workspace", "schema": "hawkerbridge",
    "app_name": "hawkerbridge", "input_mode": "live",
    "reuse_archived_geometry": "true", "experiment_id": "",
}.items():
    dbutils.widgets.text(name, default)  # noqa: F821

repo_root = Path(dbutils.widgets.get("repo_root"))  # noqa: F821
if not repo_root.is_absolute() or not (repo_root / "backend/hawkerbridge/ingest.py").exists():
    raise ValueError("Set repo_root to the uploaded bundle's absolute Workspace files path")

sys.path.insert(0, str(repo_root / "backend"))
sys.path.insert(0, str(repo_root / "databricks"))
from pipeline import run_pipeline  # noqa: E402

# COMMAND ----------

report = run_pipeline(
    spark=spark,  # noqa: F821
    repo_root=repo_root,
    catalog=dbutils.widgets.get("catalog"),  # noqa: F821
    schema=dbutils.widgets.get("schema"),  # noqa: F821
    app_name=dbutils.widgets.get("app_name"),  # noqa: F821
    input_mode=dbutils.widgets.get("input_mode"),  # noqa: F821
    reuse_archived_geometry=dbutils.widgets.get("reuse_archived_geometry").lower() == "true",  # noqa: F821
    experiment_id=dbutils.widgets.get("experiment_id"),  # noqa: F821
)
print(json.dumps(report, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC Inspect the schema's `bronze_sources`, `silver_*`, `gold_*`,
# MAGIC `quality_audit`, `pipeline_events` and `lineage_edges` tables. The `published_*`
# MAGIC views read only the publication selected by `gold_snapshots`.
# MAGIC MLflow records modelled allocation results and their baseline; it is not a
# MAGIC trained hunger predictor and does not measure real people helped.
