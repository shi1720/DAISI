"""Render original HawkerBridge publication graphics without third-party imagery."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'submission/assets'
OUT.mkdir(parents=True, exist_ok=True)
FONT = Path('/System/Library/Fonts/Supplemental')


def make(width, height, name):
    scale = width / 1200
    image = Image.new('RGB', (width, height), '#f6f3e9')
    draw = ImageDraw.Draw(image)
    def box(coords, color, radius=0):
        coords = tuple(round(v * scale) for v in coords)
        if radius:
            draw.rounded_rectangle(coords, radius=round(radius * scale), fill=color)
        else:
            draw.rectangle(coords, fill=color)
    def text(x, y, value, size, color='#f6f3e9', bold=False, serif=False):
        file = 'Georgia.ttf' if serif else 'Arial Bold.ttf' if bold else 'Arial.ttf'
        font = ImageFont.truetype(str(FONT / file), round(size * scale))
        draw.text((x * scale, y * scale), value, font=font, fill=color, spacing=round(10 * scale))
    h = height / scale
    box((0, 0, 748, h), '#123b36')
    box((48, 45, 63, 62), '#db6a43', 4)
    text(77, 40, 'HAWKERBRIDGE', 24, bold=True)
    text(50, 104, 'SINGAPORE  /  COMMUNITY CONTINUITY', 14, '#bfd1bf', True)
    text(46, 152, 'Keep the\nneighbourhood\nat the table.', 66, serif=True)
    text(50, h - 147, 'A practical support plan\nbefore a hawker centre closes.', 24, '#e0e9d9')
    text(50, h - 52, 'Shivam Gupta  •  DAISI Singapore 2026', 15, '#bfd1bf')
    text(796, 61, 'THE CAPACITY DECISION', 15, '#426158', True)
    text(792, 112, '450', 112, '#123b36', True)
    text(801, 235, 'planned meals per day', 20, '#426158')
    rows = [('S$1,500', '225 meals'), ('S$3,000', '450 meals'), ('S$6,000', '450 meals')]
    for index, (budget, meals) in enumerate(rows):
        y = 311 + index * 64
        box((792, y - 8, 1155, y + 42), '#e7ecdf' if index < 2 else '#f0d6bc', 10)
        text(807, y + 4, budget, 23, '#163e37', True)
        text(997, y + 5, meals, 20, '#163e37')
    text(801, 518, 'More budget alone\ndoes not add capacity.', 23, '#123b36', True)
    if h > 730:
        text(801, 630, '3 localities × 150 meals\nS$2,700 proposed spend', 19, '#426158')
    text(800, h - 59, 'Modelled scenario.\nNo delivered-meal claim.', 14, '#426158')
    image.save(OUT / name, optimize=True)


make(1200, 800, 'hawkerbridge-devpost-cover.png')
make(1280, 720, 'hawkerbridge-youtube-thumbnail.png')
print('Created two original publication graphics.')
