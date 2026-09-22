"""Deploy and schedule the bounded guest-retention worker from the active API image.

Copies runtime settings without printing them. The scheduler identity can invoke
only this job. Uses existing gcloud credentials and creates no credential files.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def call(args: list[str]) -> None:
    print("Running: " + " ".join(args), flush=True)
    subprocess.run(args, check=True)


def exists(args: list[str]) -> bool:
    result = subprocess.run(args, capture_output=True, text=True)
    missing = any(text in result.stderr.lower() for text in ("not_found", "not found", "cannot find job"))
    if result.returncode and not missing:
        raise RuntimeError("Unable to check the existing job; verify gcloud permissions")
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", default="asia-southeast1")
    parser.add_argument("--dry-run", action="store_true", help="Inspect expiry using an execution override on the existing job; never change its schedule or saved command")
    args = parser.parse_args()
    common = ["--project", args.project, "--region", args.region]
    job = "hawkerbridge-retention"
    job_exists = exists(["gcloud", "run", "jobs", "describe", job, *common, "--format=value(metadata.name)"])
    if args.dry_run:
        if not job_exists:
            parser.error("Deploy the retention job first, then use --dry-run to inspect it")
        call(["gcloud", "run", "jobs", "execute", job, *common,
              "--args=-m,hawkerbridge.firebase_cleanup,--limit,1000", "--wait", "--quiet"])
        return
    service = json.loads(subprocess.check_output(["gcloud", "run", "services", "describe", "hawkerbridge-api", *common, "--format=json"], text=True))
    spec = service["spec"]["template"]["spec"]
    container = spec["containers"][0]
    env = {v["name"]: v["value"] for v in container["env"] if "value" in v}
    env["PYTHONPATH"] = "/app/backend"
    with tempfile.TemporaryDirectory(prefix="hawkerbridge-retention-") as directory:
        path = Path(directory) / "env.json"
        path.write_text(json.dumps(env))
        os.chmod(path, 0o600)
        command = ["gcloud", "run", "jobs", "update" if job_exists else "create", job, *common,
                   "--image", container["image"], "--service-account", spec["serviceAccountName"],
                   "--env-vars-file", str(path), "--command", "python",
                   "--args=-m,hawkerbridge.firebase_cleanup,--limit,1000,--execute",
                   "--memory", "512Mi", "--cpu", "1", "--tasks", "1", "--parallelism", "1",
                   "--max-retries", "1", "--task-timeout", "300", "--quiet"]
        call(command)
    call(["gcloud", "run", "jobs", "execute", job, *common, "--wait", "--quiet"])
    scheduler = f"hawkerbridge-scheduler@{args.project}.iam.gserviceaccount.com"
    if not exists(["gcloud", "iam", "service-accounts", "describe", scheduler,
                   "--project", args.project, "--format=value(email)"]):
        call(["gcloud", "iam", "service-accounts", "create", "hawkerbridge-scheduler",
              "--project", args.project, "--display-name", "HawkerBridge retention scheduler", "--quiet"])
    call(["gcloud", "run", "jobs", "add-iam-policy-binding", job, *common,
          "--member", "serviceAccount:" + scheduler, "--role", "roles/run.invoker", "--quiet", "--format=value(etag)"])
    scheduled = exists(["gcloud", "scheduler", "jobs", "describe", job, "--project", args.project,
                        "--location", args.region, "--format=value(name)"])
    call(["gcloud", "scheduler", "jobs", "update" if scheduled else "create", "http", job,
          "--project", args.project, "--location", args.region,
          "--schedule", "15 * * * *", "--time-zone", "Asia/Singapore",
          "--uri", f"https://run.googleapis.com/v2/projects/{args.project}/locations/{args.region}/jobs/{job}:run",
          "--http-method", "POST", "--oauth-service-account-email", scheduler,
          "--update-headers" if scheduled else "--headers", "Content-Type=application/json", "--message-body", "{}", "--quiet"])


if __name__ == "__main__":
    main()
