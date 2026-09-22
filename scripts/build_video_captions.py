"""Create editable, approximately timed captions from the exact spoken script."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def seconds(value: str) -> int:
    minute, second = value.split(":")
    return int(minute) * 60 + int(second)


def stamp(value: float) -> str:
    total = round(value * 1000)
    return (
        f"{total // 3600000:02}:{total // 60000 % 60:02}:{total // 1000 % 60:02},{total % 1000:03}"
    )


def main() -> None:
    script = (ROOT / "submission/video-script.md").read_text()
    section = script.split("## Narration and storyboard", 1)[1].split("## Optional replacement", 1)[
        0
    ]
    headings = list(re.finditer(r"\*\*(\d:\d\d)[–-](\d:\d\d).*?\*\*", section))
    captions = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        spoken = " ".join(
            line[2:] for line in section[heading.end() : end].splitlines() if line.startswith("> ")
        )
        words = spoken.split()
        chunks, current = [], []
        for word in words:
            if current and len(" ".join([*current, word])) > 78:
                chunks.append(current)
                current = []
            current.append(word)
        if current:
            chunks.append(current)
        start_time, end_time = seconds(heading.group(1)), seconds(heading.group(2))
        consumed = 0
        for chunk in chunks:
            begin = start_time + (end_time - start_time) * consumed / len(words)
            consumed += len(chunk)
            finish = start_time + (end_time - start_time) * consumed / len(words)
            captions.append(
                f"{len(captions) + 1}\n{stamp(begin)} --> {stamp(finish)}\n"
                + "\n".join(textwrap.wrap(" ".join(chunk), 41, break_long_words=False))
            )
    target = ROOT / "submission/hawkerbridge-captions.srt"
    target.write_text("\n\n".join(captions) + "\n")
    print(f"Wrote {len(captions)} caption cues; align to the recorded voice before upload.")


if __name__ == "__main__":
    main()
