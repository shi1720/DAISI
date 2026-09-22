"""Prevent incomplete or unverified submission metadata from looking ready."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--round", choices=["1", "2"], default="1")
args = parser.parse_args()
team = json.loads((ROOT / "submission/team.json").read_text())
problems = []
if not 1 <= len(team.get("members", [])) <= 4:
    problems.append("Team must have 1–4 members")
for member in team.get("members", []):
    for key in ["name", "institution", "course", "year", "email"]:
        if not member.get(key):
            problems.append(f"{member.get('name', 'Member')}: add {key}")
    if member.get("current_singapore_ihl_enrolment_confirmed") is not True:
        problems.append(f"{member.get('name', 'Member')}: confirm current Singapore IHL enrolment")
if not (ROOT / "output/pdf/hawkerbridge-round1.pdf").exists():
    problems.append("Generate Round 1 PDF")
if args.round == "2":
    status_path = ROOT / "submission/deployment-status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    for key in [
        "databricks_app_url",
        "successful_pipeline_run_url",
        "mlflow_run_url",
        "public_or_unlisted_video_url",
    ]:
        if not status.get(key):
            problems.append(f"Round 2: verify and record {key}")
if problems:
    print("NOT READY TO SUBMIT\n" + "\n".join("- " + x for x in problems))
    raise SystemExit(1)
print("Metadata checks passed. Participant must review actual eligibility and final submission.")
