#!/usr/bin/env python3
"""Build, validate, deploy and start the real workspace path without storing secrets.

Requires a Databricks CLI profile authenticated by the user. This script never opens
accounts, accepts terms, prints credentials, changes account-level settings or treats
an unexecuted bundle as a deployment. No operation runs with shell=True.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("Running: " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="DEFAULT", help="Existing Databricks CLI authentication profile")
    parser.add_argument("--warehouse-id", required=True, help="Existing Free Edition SQL warehouse ID")
    parser.add_argument("--catalog", default="workspace")
    parser.add_argument("--schema", default="hawkerbridge")
    parser.add_argument("--app-name", default="hawkerbridge")
    parser.add_argument("--input-mode", choices=("live", "archived_replay"), default="live")
    parser.add_argument("--fresh-geometry", action="store_true", help="Request official geometry instead of checksum-verified archive reuse")
    args = parser.parse_args()
    for executable in ("databricks", "npm"):
        if not shutil.which(executable):
            parser.error(f"{executable} is required; see docs/databricks-deployment.md")
    for name in (args.catalog, args.schema):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", name):
            parser.error("Catalog and schema must be simple identifiers")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", args.app_name):
        parser.error("App name must use lowercase letters, digits and hyphens, starting with a letter")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,128}", args.warehouse_id):
        parser.error("Invalid warehouse ID")
    for relative in ("scripts/start_app.py", "requirements.txt", "frontend/package-lock.json",
                     "backend/hawkerbridge/engine.py", "data/processed/snapshot.json"):
        if not (ROOT / relative).is_file():
            parser.error(f"Missing deployment input: {relative}")

    from databricks.sdk import WorkspaceClient
    sys.path.insert(0, str(ROOT / "backend"))
    from hawkerbridge.databricks_store import DatabricksStore
    from hawkerbridge.ingest import build_snapshot

    # Read-only readiness checks happen before build or deployment mutations.
    client = WorkspaceClient(profile=args.profile)
    client.current_user.me()
    warehouse = client.warehouses.get(args.warehouse_id)
    if warehouse.enable_serverless_compute is not True:
        parser.error("Choose the existing serverless SQL warehouse for Free Edition")
    archive = build_snapshot(ROOT / "data/raw/baseline-20260922")
    print(f"Authenticated. Archive checksums verified for {len(archive['manifest']['sources'])} sources.")
    if args.input_mode == "archived_replay":
        print("Explicit ARCHIVED REPLAY selected: no live source acquisition will be claimed.")
    run(["npm", "ci"], cwd=ROOT / "frontend")
    run(["npm", "run", "build"], cwd=ROOT / "frontend")
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError("Frontend build did not produce frontend/dist/index.html")
    variables = ",".join((f"warehouse_id={args.warehouse_id}", f"catalog={args.catalog}",
                          f"schema={args.schema}", f"app_name={args.app_name}",
                          f"input_mode={args.input_mode}",
                          f"reuse_archived_geometry={str(not args.fresh_geometry).lower()}"))
    common = ["--target", "dev", "--profile", args.profile, "--var", variables]
    run(["databricks", "bundle", "validate", *common])
    run(["databricks", "bundle", "deploy", *common])
    # The app resource now exists. The pipeline grants its principal only the required table privileges.
    run(["databricks", "bundle", "run", "hawkerbridge_pipeline", *common])
    config = SimpleNamespace(databricks_warehouse_id=args.warehouse_id, catalog=args.catalog, schema=args.schema)
    snapshot = DatabricksStore(config, client=client).load_snapshot()
    metadata = snapshot.get("manifest", {}).get("databricks", {})
    if metadata.get("input_mode") != args.input_mode:
        raise RuntimeError("Published input mode differs from the requested deployment")
    run(["databricks", "bundle", "run", "hawkerbridge_app", *common])
    app = client.apps.get(args.app_name)
    print(json.dumps({"app_url": app.url, "publication_id": metadata.get("publication_id"),
                      "input_mode": metadata.get("input_mode"), "mlflow_run_id": metadata.get("mlflow_run_id"),
                      "next_check": "Sign in through the app URL and complete the owner-isolation checklist"}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError, RuntimeError, ValueError) as exc:
        print(f"Deployment stopped: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
