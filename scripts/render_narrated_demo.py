"""Assemble real hosted footage, disclosed synthetic narration and burned captions.

Pillow renders captions so this also works with FFmpeg builds without libass.
Word timings come from transcription of the actual generated audio, not estimates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def timestamp(value: float) -> str:
    ms = round(value * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--footage", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/video/hawkerbridge-demo-narrated.mp4")
    parser.add_argument("--scenes", type=Path, default=ROOT / "submission/narration-scenes.json")
    parser.add_argument("--narration", type=Path, default=ROOT / "output/video/narration")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path, preserving the previous render")
    scenes = json.loads(args.scenes.read_text())
    work = args.narration / "render"
    work.mkdir(parents=True, exist_ok=True)
    total = 175
    rate = 24000
    samples = bytearray(total * rate * 2)
    cues = []
    for n, scene in enumerate(scenes, 1):
        with wave.open(str(args.narration / f"scene-{n:02}.wav"), "rb") as audio:
            assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, rate)
            raw = audio.readframes(audio.getnframes())
            start = round(scene["start"] * rate) * 2
            assert start + len(raw) <= round(scene["end"] * rate) * 2
            samples[start:start + len(raw)] = raw
        transcript = json.loads((args.narration / f"scene-{n:02}-words.json").read_text())
        group = []
        for word in transcript["words"]:
            proposed = " ".join(w["word"].strip() for w in [*group, word])
            if group and (len(proposed) > 87 or word["end"] - group[0]["start"] > 5.5):
                cues.append({"start": scene["start"] + group[0]["start"], "end": scene["start"] + group[-1]["end"], "text": " ".join(w["word"].strip() for w in group)})
                group = []
            group.append(word)
            if word["word"].rstrip().endswith((".", "?", "!")) and len(group) >= 5:
                cues.append({"start": scene["start"] + group[0]["start"], "end": scene["start"] + group[-1]["end"], "text": " ".join(w["word"].strip() for w in group)})
                group = []
        if group:
            cues.append({"start": scene["start"] + group[0]["start"], "end": scene["start"] + group[-1]["end"], "text": " ".join(w["word"].strip() for w in group)})
    mixed = work / "narration.wav"
    with wave.open(str(mixed), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(samples)
    for i, cue in enumerate(cues):
        next_start = cues[i + 1]["start"] if i + 1 < len(cues) else total
        cue["end"] = min(next_start, cue["end"] + 0.15)
        cue["text"] = cue["text"].replace("Hawker Bridge", "HawkerBridge")
    srt = "\n\n".join(f"{i}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{textwrap.fill(c['text'], width=47)}" for i, c in enumerate(cues, 1)) + "\n"
    (ROOT / "submission/hawkerbridge-captions.srt").write_text(srt)
    (work / "cues.json").write_text(json.dumps(cues, indent=2))
    fonts = [Path("/System/Library/Fonts/Supplemental/Arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    font_path = next((p for p in fonts if p.exists()), None)
    if not font_path:
        parser.error("Install Arial or DejaVu Sans to render clear captions")
    font = ImageFont.truetype(str(font_path), 30)
    small = ImageFont.truetype(str(font_path), 17)
    width, height = 1600, 900

    def frame(path: Path, caption: str = "") -> None:
        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)
        # Clear disclosure visible in the exported video as well as its description.
        label = "HAWKERBRIDGE  |  HOSTED DEMO  |  AI NARRATION"
        draw.rounded_rectangle((width - 515, 10, width - 14, 42), radius=8, fill=(18, 59, 54, 235))
        draw.text((width - 500, 17), label, font=small, fill="white")
        if caption:
            lines = textwrap.wrap(caption, width=47)
            assert len(lines) <= 2
            box_width = max(draw.textlength(line, font=font) for line in lines) + 56
            box_height = 40 * len(lines) + 22
            left = (width - box_width) / 2
            top = height - box_height - 18
            draw.rounded_rectangle((left, top, left + box_width, top + box_height), radius=9, fill=(10, 26, 24, 238))
            for i, line in enumerate(lines):
                draw.text(((width - draw.textlength(line, font=font)) / 2, top + 9 + i * 40), line, font=font, fill="white")
        image.save(path)

    blank = work / "blank.png"
    frame(blank)
    segments = []
    cursor = 0.0
    for i, cue in enumerate(cues):
        if cue["start"] > cursor:
            segments.append((blank, cue["start"] - cursor))
        path = work / f"caption-{i:03}.png"
        frame(path, cue["text"])
        segments.append((path, cue["end"] - cue["start"]))
        cursor = cue["end"]
    if cursor < total:
        segments.append((blank, total - cursor))
    concat = work / "captions.ffconcat"
    if "'" in str(work):
        parser.error("Output directory must not contain a quote")
    concat.write_text("ffconcat version 1.0\n" + "".join(f"file '{path.resolve()}'\nduration {seconds:.6f}\n" for path, seconds in segments if seconds > 0) + f"file '{blank.resolve()}'\n")
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-i", str(args.footage),
        "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(mixed),
        "-filter_complex", "[0:v]fps=25,scale=1600:900,tpad=stop_mode=clone:stop_duration=5[base];[base][1:v]overlay=0:0:eof_action=repeat[v]",
        "-map", "[v]", "-map", "2:a:0", "-t", str(total), "-r", "25",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(args.output),
    ], check=True)
    report = {"video": str(args.output.relative_to(ROOT)), "duration_seconds": total,
              "footage_sha256": hashlib.sha256(args.footage.read_bytes()).hexdigest(),
              "video_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
              "narrator": "OpenAI gpt-4o-mini-tts built-in cedar voice; synthetic, not a voice clone",
              "captions": "Word timestamps from whisper-1 transcription of each actual narration clip",
              "caption_count": len(cues), "source": "Actual hosted product recording; see capture provenance"}
    (args.output.parent / "narrated-provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
