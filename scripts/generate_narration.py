"""Create disclosed synthetic narration and word-timed captions for real demo footage.

Uses OpenAI's built-in cedar voice, never a participant voice clone. Reads the API
key from OPENAI_API_KEY or a non-echoing terminal prompt and never saves it.
Existing clips are reused. Input is an explicitly reviewed JSON scene list.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
from pathlib import Path

import httpx


def duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)
    ], text=True).strip())


def checked(response: httpx.Response) -> httpx.Response:
    if not response.is_success:
        code = response.json().get("error", {}).get("code", "unspecified")
        raise RuntimeError(f"OpenAI audio request failed: HTTP {response.status_code}, code {code}")
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenes", type=Path, default=Path("submission/narration-scenes.json"))
    parser.add_argument("--output", type=Path, default=Path("output/video/narration"))
    parser.add_argument("--only", default="", help="Comma-separated scene numbers, e.g. 1,2")
    args = parser.parse_args()
    scenes = json.loads(args.scenes.read_text())
    selected = {int(n) for n in args.only.split(",") if n} or set(range(1, len(scenes) + 1))
    args.output.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("OPENAI_API_KEY") or getpass.getpass("OpenAI key (not stored): ")
    if not key:
        parser.error("An API key is required")
    with httpx.Client(base_url="https://api.openai.com/v1", headers={"Authorization": f"Bearer {key}"}, timeout=120) as client:
        for number, scene in enumerate(scenes, 1):
            if number not in selected:
                continue
            raw = args.output / f"scene-{number:02}-raw.wav"
            clip = args.output / f"scene-{number:02}.wav"
            transcript = args.output / f"scene-{number:02}-words.json"
            if not raw.exists():
                response = checked(client.post("/audio/speech", json={
                    "model": "gpt-4o-mini-tts", "voice": "cedar", "response_format": "wav",
                    "input": scene["text"],
                    "instructions": "Warm, clear documentary narration in natural English. Sound thoughtful and confident, not like an advertisement. Speak at about 155 words per minute, with short pauses between sentences. Pronounce HawkerBridge as Hawker Bridge. Say all numbers clearly. No added words, sound effects or music. This is a generic narrator, not an imitation of any person.",
                }))
                raw.write_bytes(response.content)
            available = scene["end"] - scene["start"] - 0.25
            pace = max(1.0, duration(raw) / available)
            if pace > 1.18:
                raise RuntimeError(f"Scene {number} is too long for comfortable narration; shorten the reviewed script")
            if not clip.exists():
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(raw),
                                "-af", f"atempo={pace:.6f},loudnorm=I=-16:TP=-1.5:LRA=9",
                                "-ar", "24000", "-ac", "1", str(clip)], check=True)
            if not transcript.exists():
                with clip.open("rb") as audio:
                    response = checked(client.post("/audio/transcriptions", files={"file": (clip.name, audio, "audio/wav")}, data={
                        "model": "whisper-1", "language": "en", "response_format": "verbose_json",
                        "timestamp_granularities[]": "word", "prompt": scene["text"],
                    }))
                transcript.write_text(json.dumps(response.json(), indent=2))
            print(f"Scene {number}: {duration(clip):.2f} seconds, slot {scene['start']} to {scene['end']}, captions generated", flush=True)
    key = ""


if __name__ == "__main__":
    main()
