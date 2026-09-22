"""Check required artifacts and evidence without treating a draft as submitted."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--round", choices=["1", "2"], default="1")
args = parser.parse_args()
team = json.loads((ROOT / "submission/team.json").read_text())
problems = []
if not 1 <= len(team.get("members", [])) <= 4:
    problems.append("Team must have 1-4 members")
for member in team.get("members", []):
    for key in ["name", "institution", "course", "year", "email"]:
        if not member.get(key):
            problems.append(f"{member.get('name', 'Member')}: add {key}")
    if member.get("current_singapore_ihl_enrolment_confirmed") is not True:
        problems.append(f"{member.get('name', 'Member')}: confirm current Singapore IHL enrolment")


def check_pdf(relative: str, minimum: int, maximum: int) -> None:
    path = ROOT / relative
    if not path.is_file():
        problems.append(f"Generate {relative}")
        return
    try:
        count = len(PdfReader(path).pages)
    except Exception:
        problems.append(f"Cannot read {relative}")
        return
    if not minimum <= count <= maximum:
        problems.append(f"{relative}: expected {minimum}-{maximum} pages, found {count}")


check_pdf("output/pdf/hawkerbridge-round1.pdf", 3, 3)
if args.round == "2":
    status_path = ROOT / "submission/deployment-status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    for key in [
        "databricks_app_url",
        "successful_pipeline_run_url",
        "mlflow_run_url",
        "public_or_unlisted_video_url",
    ]:
        value = status.get(key)
        parsed = urlparse(value or "")
        if parsed.scheme != "https" or not parsed.netloc:
            problems.append(f"Round 2: verify and record {key}")
    if status.get("databricks_workspace_execution_verified") is not True:
        problems.append("Round 2: actual Databricks workspace execution is not verified")
    check_pdf("output/pdf/hawkerbridge-final-pitch.pdf", 1, 10)
    for relative in ["submission/devpost-description.md", "submission/whats-next.md"]:
        if not (ROOT / relative).is_file():
            problems.append(f"Round 2: add {relative}")
    if not list((ROOT / "docs/screenshots").glob("*.png")):
        problems.append("Round 2: add the verified product screenshots")
if problems:
    print("NOT READY TO SUBMIT\n" + "\n".join("- " + x for x in problems))
    raise SystemExit(1)
print(
    "Artifact and metadata checks passed. Review eligibility, judge access and the actual submission."
)
