# Databricks notebook source
# MAGIC %md
# MAGIC # HawkerBridge · one source-to-decision run
# MAGIC This notebook uses the same ingestion and planning code as the application.
# MAGIC A published snapshot is committed only after data checks and measured optimiser
# MAGIC evaluation succeed. `archived_replay` is explicitly labelled and never an
# MAGIC automatic replacement for a failed live refresh. No personal beneficiary data.

# COMMAND ----------

# Initialize the notebook's managed Spark session in its first Python command.
# Imported helpers use this session later; a lazy placeholder cannot be passed
# into module code before the serverless notebook has initialized it.
import json
import sys
import tempfile
from pathlib import Path

from databricks.connect import DatabricksSession
from databricks.sdk import WorkspaceClient

spark = DatabricksSession.builder.getOrCreate()
spark.sql("SELECT 1 AS session_ready").collect()

# COMMAND ----------

# Job parameters are automatically exposed as widgets by Lakeflow Jobs.
for name, default in {
    "repo_root": "", "catalog": "workspace", "schema": "hawkerbridge",
    "app_name": "hawkerbridge", "input_mode": "live",
    "reuse_archived_geometry": "true", "experiment_id": "",
}.items():
    dbutils.widgets.text(name, default)  # noqa: F821

workspace_root = Path(dbutils.widgets.get("repo_root"))  # noqa: F821
if not workspace_root.is_absolute() or ".." in workspace_root.parts or not str(workspace_root).startswith("/Workspace/"):
    raise ValueError("Set repo_root to the uploaded bundle's absolute Workspace files path")

# Read the explicit, bounded input set through the Workspace API. Mounted
# Workspace files can return EIO on serverless during imports; a local staged
# copy also keeps later helper reads independent of that filesystem transport.
workspace = WorkspaceClient()
staged_sources = tempfile.TemporaryDirectory(prefix="hawkerbridge-source-")
repo_root = Path(staged_sources.name)
archive = "data/raw/baseline-20260922"
required_files = [
    "backend/hawkerbridge/__init__.py", "backend/hawkerbridge/ingest.py",
    "backend/hawkerbridge/engine.py", "databricks/pipeline.py",
    *[f"{archive}/{name}" for name in (
        "provenance.json", "closures.json", "population2020.json",
        "planning_areas.geojson", "subzones.geojson", "waste.json",
    )],
]
for relative in required_files:
    destination = repo_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with workspace.workspace.download(str(workspace_root / relative)) as source:
        destination.write_bytes(source.read())

# The geometry cache needs only retrieval metadata and raw checksummed bytes.
# Keep it tied to the shipped archive even if the public app's snapshot has
# since been replaced by a newer Databricks publication.
provenance = json.loads((repo_root / archive / "provenance.json").read_text())
cache_path = repo_root / "data/processed/snapshot.json"
cache_path.parent.mkdir(parents=True, exist_ok=True)
cache_path.write_text(json.dumps({"manifest": {"sources": provenance["sources"]}}))

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
dbutils.notebook.exit(json.dumps(report))  # noqa: F821

# COMMAND ----------

# MAGIC %md
# MAGIC Inspect the schema's `bronze_sources`, `silver_*`, `gold_*`,
# MAGIC `quality_audit`, `pipeline_events` and `lineage_edges` tables. The `published_*`
# MAGIC views read only the publication selected by `gold_snapshots`.
# MAGIC MLflow records modelled allocation results and their baseline; it is not a
# MAGIC trained hunger predictor and does not measure real people helped.
