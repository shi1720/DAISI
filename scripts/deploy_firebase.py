"""Build and deploy the public Firebase site and its isolated Singapore API.

Uses existing gcloud/Firebase CLI logins. No service-account key is created.
The identity project may differ from the billing-enabled hosting project.
Provisioning instructions and the exact IAM grants are in docs/firebase-deployment.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], *, cwd: Path = ROOT) -> None:
    print("Running: " + " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Billing-enabled hosting/compute project")
    parser.add_argument("--identity-project", required=True, help="Dedicated Firebase Auth and Firestore project")
    parser.add_argument("--web-app-id", required=True, help="Existing Firebase Web App in the identity project")
    parser.add_argument("--site", default="hawkerbridge-sg")
    parser.add_argument("--region", default="asia-southeast1")
    parser.add_argument("--firebase-cli", default="firebase")
    parser.add_argument("--skip-build", action="store_true", help="Reuse an already verified frontend/dist")
    args = parser.parse_args()
    for value in (args.project, args.identity_project, args.site, args.region):
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,62}", value):
            parser.error("Project, site and region identifiers must be lowercase letters, digits and hyphens")
    for executable in ("gcloud", "npm", args.firebase_cli):
        if not shutil.which(executable):
            parser.error(f"Missing executable: {executable}")
    hosting = json.loads((ROOT / "firebase.json").read_text())
    if hosting["hosting"]["site"] != args.site or hosting["hosting"]["rewrites"][0]["run"]["region"] != args.region:
        parser.error("firebase.json site and region must match the requested deployment")
    service = "hawkerbridge-api"
    account = f"hawkerbridge-runtime@{args.project}.iam.gserviceaccount.com"
    cli = args.firebase_cli
    config = json.loads(subprocess.check_output([
        cli, "apps:sdkconfig", "WEB", args.web_app_id, "--project", args.identity_project, "--json"
    ], text=True, cwd=ROOT))["result"]
    sdk = json.loads(config["sdkConfig"]) if isinstance(config.get("sdkConfig"), str) else config.get("sdkConfig", config)
    api_key = sdk["apiKey"]
    env = {
        "HAWKERBRIDGE_AUTH_MODE": "firebase", "HAWKERBRIDGE_STORAGE": "firestore",
        "HAWKERBRIDGE_SECURE_COOKIES": "true",
        "HAWKERBRIDGE_ALLOWED_ORIGINS": f"https://{args.site}.web.app,https://{args.site}.firebaseapp.com",
        "HAWKERBRIDGE_FIREBASE_PROJECT": args.identity_project,
        "HAWKERBRIDGE_FIREBASE_API_KEY": api_key,
        "HAWKERBRIDGE_FIRESTORE_DATABASE": "(default)",
    }
    if not args.skip_build:
        run(["npm", "ci"], cwd=ROOT / "frontend")
        run(["npm", "run", "build"], cwd=ROOT / "frontend")
    if not (ROOT / "frontend/dist/index.html").exists():
        parser.error("Build frontend/dist before deploying")
    tag = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    image = f"{args.region}-docker.pkg.dev/{args.project}/hawkerbridge/api:{tag}"
    # The upload whitelist excludes credentials, local databases and unrelated folders.
    run(["gcloud", "builds", "submit", ".", "--project", args.project,
         "--config", "cloudbuild.yaml", "--substitutions", f"_IMAGE={image}", "--quiet"])
    with tempfile.TemporaryDirectory(prefix="hawkerbridge-deploy-") as directory:
        env_path = Path(directory) / "runtime.json"
        env_path.write_text(json.dumps(env))
        os.chmod(env_path, 0o600)
        run(["gcloud", "run", "deploy", service, "--project", args.project,
             "--region", args.region, "--image", image, "--service-account", account,
             "--env-vars-file", str(env_path), "--port", "8080", "--memory", "1Gi",
             "--cpu", "1", "--concurrency", "8", "--min-instances", "0",
             "--max-instances", "2", "--timeout", "60", "--allow-unauthenticated", "--quiet"])
    run([cli, "deploy", "--only", "hosting", "--project", args.project, "--non-interactive"])
    print(f"Deployed https://{args.site}.web.app. Run scripts/smoke_hosted.py before announcing verification.")


if __name__ == "__main__":
    main()
