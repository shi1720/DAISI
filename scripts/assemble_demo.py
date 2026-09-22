"""Combine the actual silent browser recording with Shivam's supplied narration.

No voice is fabricated. A silent preview is possible without --voiceover. Output is
capped at 175 seconds, below the competition's three-minute maximum. This does not
upload a video or claim the local recording runs inside Databricks.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def duration(path: Path) -> float:
    output = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        text=True,
    )
    return float(json.loads(output)["format"]["duration"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--footage", type=Path, default=ROOT / "output/video/hawkerbridge-demo-silent.webm"
    )
    parser.add_argument(
        "--voiceover",
        type=Path,
        help="A real recording of the participant reading submission/video-script.md",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "output/video/hawkerbridge-demo.mp4")
    args = parser.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("Install FFmpeg from its official distribution or a trusted package manager")
    if not args.footage.is_file():
        parser.error(f"Footage is missing: {args.footage}")
    if args.output.exists():
        parser.error("Choose a new output filename; existing recordings are not overwritten")
    if args.voiceover and (not args.voiceover.is_file() or duration(args.voiceover) > 175):
        parser.error(
            "Voiceover must exist and last at most 175 seconds; rerecord or trim intentionally"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-hide_banner", "-i", str(args.footage)]
    if args.voiceover:
        command += [
            "-i",
            str(args.voiceover),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-af",
            "apad",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
        ]
    else:
        command += ["-an"]
    command += [
        "-vf",
        "tpad=stop_mode=clone:stop_duration=5",
        "-t",
        "175",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    subprocess.run(command, check=True)
    print(
        f"Created {args.output}. Watch the complete video and align the editable captions before upload."
    )


if __name__ == "__main__":
    main()
