"""Package only explicit submission deliverables; never include credentials or local state."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_source(revision: str) -> None:
    """Export committed source without .git, machine state or unrelated workspace files."""
    tracked = (
        subprocess.check_output(["git", "ls-tree", "-rz", "--name-only", revision], cwd=ROOT)
        .decode()
        .split("\0")
    )
    allowed_roots = {
        "backend",
        "browser-tests",
        "data",
        "databricks",
        "docs",
        "frontend",
        "resources",
        "research",
        "scripts",
        "submission",
        "tests",
        ".github",
    }
    allowed_files = {
        ".env.example",
        ".gitignore",
        ".gitattributes",
        "LICENSE",
        "NOTICE.md",
        "README.md",
        "SECURITY.md",
        "START_HERE.md",
        "pyproject.toml",
        "uv.lock",
        "requirements.txt",
        "app.yaml",
        "databricks.yml",
        "Dockerfile", ".dockerignore", ".gcloudignore", "cloudbuild.yaml",
        "firebase.json", "firebase-data.json", "firestore.rules", "firestore.indexes.json",
    }
    names = [
        name
        for name in tracked
        if name and (name in allowed_files or Path(name).parts[0] in allowed_roots)
    ]
    destination = ROOT / "output/HawkerBridge-source.zip"
    files = []
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            raw = subprocess.check_output(["git", "show", f"{revision}:{name}"], cwd=ROOT)
            archive.writestr("HawkerBridge/" + name, raw)
            files.append(
                {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            )
        archive.writestr(
            "HawkerBridge/SOURCE_MANIFEST.json",
            json.dumps(
                {
                    "repository": "https://github.com/shi1720/DAISI",
                    "revision": revision,
                    "note": "Committed source export. Install dependencies and build the frontend using README.md. Presentation/video deliverables are in the separate submission pack; these links in START_HERE.md require that pack.",
                    "files": files,
                },
                indent=2,
            )
            + "\n",
        )
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for item in files:
            assert (
                hashlib.sha256(archive.read("HawkerBridge/" + item["path"])).hexdigest()
                == item["sha256"]
            )
    print(f"Verified {len(files)} committed source files in {destination}")


def main() -> None:
    paths = [
        ROOT / "START_HERE.md",
        ROOT / "README.md",
        ROOT / "LICENSE",
        ROOT / "NOTICE.md",
        ROOT / "data/sources.json",
        ROOT / "data/processed/evaluation.json",
        ROOT / "docs/business-case.md",
        ROOT / "docs/evaluation.md",
        ROOT / "docs/rules-and-eligibility.md",
        ROOT / "docs/databricks-deployment.md",
        ROOT / "output/pdf/hawkerbridge-round1.pdf",
        ROOT / "output/pdf/hawkerbridge-final-pitch.pdf",
        ROOT / "output/pdf/hawkerbridge-concept-note.pdf",
        ROOT / "output/pdf/hawkerbridge-video-narration.pdf",
        ROOT / "output/pdf/example-continuity-plan.pdf",
        ROOT / "output/presentations/hawkerbridge-round1.pptx",
        ROOT / "output/presentations/hawkerbridge-final-pitch.pptx",
        ROOT / "output/video/hawkerbridge-demo-narrated.mp4",
        ROOT / "output/demo-footage/timeline.json",
        ROOT / "output/video/narrated-provenance.json",
    ]
    for folder, patterns in {
        "docs": ["*.md"],
                "docs/screenshots": ["*.png", "README.md", "provenance.json"],
        "submission": ["*.md", "*.srt", "deployment-status.json", "team.json"],
        "submission/assets": ["*.png"],
        "output": ["example-continuity-plan.csv", "example-continuity-plan.json", "hosted-smoke.json", "hosted-restart-smoke.json"],
        "data/processed": ["databricks-publication.json", "databricks-evaluation.json"],
        "output/video": [
            "hawkerbridge-demo-narrated.mp4",
            "narrated-provenance.json",
        ],
        "scripts": ["render_narrated_demo.py", "check_submission.py"],
    }.items():
        for pattern in patterns:
            paths.extend((ROOT / folder).glob(pattern))
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    package_source(revision)
    paths.append(ROOT / "output/HawkerBridge-source.zip")
    paths = sorted(set(paths))
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.is_file()]
    if missing:
        raise SystemExit(f"Required files missing: {missing}")
    manifest = {
        "product": "HawkerBridge",
        "project_owner": "Shivam Gupta",
        "assembled_at": datetime.now(UTC).isoformat(),
        "repository": "https://github.com/shi1720/DAISI",
        "repository_revision_at_assembly": revision,
        "note": "Materials for review, not proof of submission, student eligibility, cloud deployment or observed social impact. See submission/deployment-status.json. The complete application source is in the included output/HawkerBridge-source.zip and in the repository.",
        "files": [
            {
                "path": str(p.relative_to(ROOT)),
                "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for p in paths
        ],
    }
    destination = ROOT / "output/HawkerBridge-submission-pack.zip"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "HawkerBridge/READ_THIS_FIRST.txt",
            "This archive contains submission materials, screenshots, video assets and a separate source archive at output/HawkerBridge-source.zip. Extract that source archive into a separate directory and follow its README.md to run the app and checks. The source is also at https://github.com/shi1720/DAISI. Start with START_HERE.md. The final narrated hosted demo is output/video/hawkerbridge-demo-narrated.mp4. It has burned captions and disclosed generic AI narration. Cloud execution evidence is in data/processed/databricks-publication.json. Check submission/deployment-status.json for actual public links and verification. Participant eligibility details remain a separate submission gate.\n",
        )
        for path in paths:
            archive.write(path, "HawkerBridge/" + str(path.relative_to(ROOT)))
        archive.writestr("HawkerBridge/BUILD_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for item in manifest["files"]:
            assert (
                hashlib.sha256(archive.read("HawkerBridge/" + item["path"])).hexdigest()
                == item["sha256"]
            )
    if destination.stat().st_size > 35_000_000:
        raise SystemExit("Submission archive exceeds Devpost 35 MB limit")
    print(f"Verified {len(paths)} files in {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
