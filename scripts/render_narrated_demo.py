"""Assemble real hosted footage, disclosed synthetic narration and burned captions.

Pillow renders captions so this also works with FFmpeg builds without libass.
Word timings come from transcription of the actual generated audio, not estimates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import textwrap
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def timestamp(value: float) -> str:
    ms = round(value * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def normal_word(value: str) -> str:
    return re.sub(r"\W", "", value).casefold()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--footage", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/video/hawkerbridge-demo-narrated.mp4")
    parser.add_argument("--scenes", type=Path, default=ROOT / "submission/narration-scenes.json")
    parser.add_argument("--narration", type=Path, default=ROOT / "output/video/narration")
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.footage.is_file():
        parser.error("Provide the verified recording file")
    if args.output.exists():
        parser.error("Choose a new output path, preserving the previous render")
    args.output.parent.mkdir(parents=True, exist_ok=True)
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
        # Whisper's word records omit punctuation. Restore it only when the
        # transcript tokens align exactly, retaining the actual word timings.
        tokens = re.findall(r"\w+(?:['’]\w+)*[.,;:!?]*", transcript.get("text", ""))
        words = transcript["words"]
        if len(tokens) == len(words) and all(normal_word(token) == normal_word(word["word"]) for token, word in zip(tokens, words, strict=True)):
            words = [word | {"word": token} for token, word in zip(tokens, words, strict=True)]
        group = []
        for word in words:
            proposed = " ".join(w["word"].strip() for w in [*group, word])
            if group and (len(proposed) > 87 or len(textwrap.wrap(proposed, width=47)) > 2
                          or word["end"] - group[0]["start"] > 5.5):
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
    intro = work / "intro.png"
    title = Image.new("RGBA", (width, height), "#123B36")
    ink = ImageDraw.Draw(title)
    ink.rounded_rectangle((92, 88, 156, 152), radius=17, fill="#EDEEDC")
    ink.arc((107, 105, 141, 139), 180, 360, fill="#123B36", width=4)
    ink.line((107, 122, 141, 122), fill="#123B36", width=4)
    ink.line((107, 122, 107, 137), fill="#123B36", width=4)
    ink.line((141, 122, 141, 137), fill="#123B36", width=4)
    ink.text((178, 98), "HawkerBridge", font=ImageFont.truetype(str(font_path), 42), fill="#F7F6F0")
    large = ImageFont.truetype(str(font_path), 72)
    ink.text((96, 260), "A closure notice tells us when.", font=large, fill="#F7F6F0")
    ink.text((96, 356), "What should we do next?", font=large, fill="#F7F6F0")
    ink.rounded_rectangle((98, 491, 195, 499), radius=4, fill="#E89766")
    ink.text((98, 547), "Keep the neighbourhood at the table.", font=ImageFont.truetype(str(font_path), 34), fill="#C2D1BA")
    ink.text((98, 647), "Shivam Gupta   /   DAISI Singapore 2026   /   C3 KopilamAI", font=ImageFont.truetype(str(font_path), 24), fill="#C2D1BA")
    title.save(intro)
    outro = work / "outro.png"
    closing = Image.new("RGBA", (width, height), "#123B36")
    ink = ImageDraw.Draw(closing)
    ink.text((100, 160), "HawkerBridge", font=ImageFont.truetype(str(font_path), 74), fill="#F7F6F0")
    ink.text((104, 280), "Put a practical planning decision to the test.", font=ImageFont.truetype(str(font_path), 43), fill="#C2D1BA")
    ink.rounded_rectangle((104, 408, 1490, 536), radius=18, fill="#F7F6F0")
    ink.text((145, 437), "hawkerbridge-sg.web.app", font=ImageFont.truetype(str(font_path), 64), fill="#123B36")
    ink.text((104, 606), "Shivam Gupta   /   DAISI Singapore 2026", font=ImageFont.truetype(str(font_path), 30), fill="#C2D1BA")
    ink.text((104, 670), "github.com/shi1720/DAISI", font=ImageFont.truetype(str(font_path), 28), fill="#C2D1BA")
    closing.save(outro)

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
        "-loop", "1", "-i", str(intro),
        "-loop", "1", "-i", str(outro),
        "-filter_complex", "[0:v]fps=25,scale=1600:900,tpad=stop_mode=clone:stop_duration=5[base];[base][3:v]overlay=0:0:enable='lt(t,8.5)'[titled];[titled][4:v]overlay=0:0:enable='gte(t,169)'[ended];[ended][1:v]overlay=0:0:eof_action=repeat[v]",
        "-map", "[v]", "-map", "2:a:0", "-t", str(total), "-r", "25",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(args.output),
    ], check=True)
    video_path = args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output
    report = {"video": str(video_path), "duration_seconds": total,
              "footage_sha256": hashlib.sha256(args.footage.read_bytes()).hexdigest(),
              "video_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
              "narrator": "OpenAI gpt-4o-mini-tts built-in cedar voice; synthetic, not a voice clone",
              "captions": "Word timestamps from whisper-1 transcription of each actual narration clip",
              "caption_count": len(cues), "opening_title_seconds": 8.5,
              "closing_title_seconds": 6,
              "source": "Actual hosted product recording with a clearly separate opening title card; see capture provenance"}
    (args.output.parent / "narrated-provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
