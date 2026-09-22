"""Restore unedited template masters/layouts after an Artifact Tool import/export.

Artifact Tool currently rewrites placeholder identities in inherited masters. Copying
those unchanged source parts preserves the official organizer template exactly;
all edited slide content and notes remain the Artifact Tool-authored output.
"""

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

source, candidate = map(Path, sys.argv[1:])
with ZipFile(source) as origin, ZipFile(candidate) as generated:
    parts = {name: generated.read(name) for name in generated.namelist()}
    for name in origin.namelist():
        if name.startswith(("ppt/slideMasters/", "ppt/slideLayouts/", "ppt/theme/")):
            parts[name] = origin.read(name)
target = candidate.with_suffix(".restored.pptx")
with ZipFile(target, "w", ZIP_DEFLATED) as output:
    for name, value in parts.items():
        output.writestr(name, value)
target.replace(candidate)
