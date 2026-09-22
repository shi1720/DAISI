"""Build the supplementary concept note and verbatim narration from tracked sources.

The official three-slide Round 1 PDF remains the primary entry. Render these files
with Poppler and inspect them whenever content or layout changes.
"""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf"
FOREST = colors.HexColor("#123F35")
INK = colors.HexColor("#203C37")
MUTED = colors.HexColor("#65776E")
ORANGE = colors.HexColor("#CB6039")


def footer(canvas, doc):
    canvas.setFillColor(FOREST)
    canvas.rect(0, A4[1] - 10, A4[0], 10, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#D8E0D8"))
    canvas.line(44, 38, A4[0] - 44, 38)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(44, 24, "HAWKERBRIDGE  /  DAISI SINGAPORE 2026")
    canvas.drawRightString(A4[0] - 44, 24, str(doc.page))


def style(name, size, leading, color=INK, **kw):
    return ParagraphStyle(
        name,
        fontName="Helvetica",
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=TA_LEFT,
        spaceAfter=9,
        **kw,
    )


def build_concept():
    body = style("body", 10.1, 14)
    h = ParagraphStyle(
        "heading",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=FOREST,
        spaceBefore=9,
        spaceAfter=5,
    )
    parts = [
        Paragraph("C3 / KOPILAMAI", style("eyebrow", 9, 12, ORANGE)),
        Paragraph("HawkerBridge", style("title", 31, 36, FOREST)),
        Paragraph("A closure continuity desk for Singapore", style("subtitle", 15, 19)),
        Paragraph("Project owner and presenter: Shivam Gupta", style("byline", 9, 13, MUTED)),
        Spacer(1, 5),
    ]
    sections = [
        (
            "The decision behind a closure notice",
            "A coordinator knows when a hawker centre closes. The harder task is deciding which neighbourhoods warrant a closer look and how to use a limited support budget. In the dated NEA snapshot, 17 centres with 1,025 listed food stalls have scheduled closures on 28 September 2026. This measures infrastructure disruption, not hunger.",
        ),
        (
            "A proposal a coordinator can review",
            "HawkerBridge compares closure dates and nearby alternatives, preserves alternatives across planning-area boundaries, and allocates planned meals under explicit budget, capacity and distance constraints. The user can test cleaning-date changes, inspect uncertainty, save a private proposal and export its assumptions and sources for review. Proposed collection localities require field verification.",
        ),
        (
            "A useful result",
            "At the demonstration assumptions of S$4 per meal, S$300 setup and 150 meals per locality, a S$1,500 budget supports a 225-meal proposal. Both S$3,000 and S$6,000 support 450 planned meals at S$2,700 cost. With a three-locality cap, capacity is the limit. A coordinator can verify more capacity before seeking additional funding.",
        ),
        (
            "Data and Databricks architecture",
            "Five official datasets combine NEA closures and stall counts, Census 2020 subzone/age populations, URA planning-area and subzone boundaries, and national food-waste context. A Lakeflow Job archives Bronze payloads, validates Silver tables, evaluates Gold allocations and publishes only after checks pass. Unity Catalog governs access, MLflow records scenario comparisons, and a Databricks App serves the planning workflow. The verified workspace run passed 12 quality gates and recorded 9 MLflow scenarios. Firebase provides the public interface using the published snapshot.",
        ),
        (
            "Impact and a sustainable buyer",
            "The first buyer hypothesis is an estate operator or funded community organisation. A proposed S$1,000 pilot tests coordinator time, factual omissions and venue feasibility before a S$250-500 monthly subscription. Prices and benefits are unvalidated. Free Edition supports the challenge build; paying customers require paid hosting and measured support costs.",
        ),
    ]
    for heading, text in sections:
        parts.extend([Paragraph(heading, h), Paragraph(escape(text), body)])
    parts += [
        Paragraph("Interpretation limits", h),
        Paragraph(
            "Distances use geographic representative points and straight lines. Census populations are from 2020. Unresolved closure dates remain explicit. Uptake, costs and capacities are assumptions, and the product does not book venues or dispatch food.",
            style("limits", 9, 12, MUTED),
        ),
        Paragraph(
            'Sources: <link href="https://data.gov.sg">data.gov.sg</link> (NEA closures, Census 2020, URA 2019 boundaries, NEA waste). Reproducible dataset IDs, dates and checksums: <link href="https://github.com/shi1720/DAISI">github.com/shi1720/DAISI</link>. Snapshot: 22 September 2026.',
            style("sources", 8, 10, MUTED),
        ),
    ]
    SimpleDocTemplate(
        str(OUTPUT / "hawkerbridge-concept-note.pdf"),
        pagesize=A4,
        topMargin=34,
        bottomMargin=51,
        leftMargin=44,
        rightMargin=44,
        title="HawkerBridge - Concept note",
        author="Shivam Gupta",
    ).build(parts, onFirstPage=footer, onLaterPages=footer)


def build_narration():
    scenes = json.loads((ROOT / "submission/narration-scenes.json").read_text())
    labels = ["Closure decision", "Access and cleaning scenario", "S$1,500 proposal", "Capacity ceiling", "Save and export a draft", "Databricks evidence and pilot"]
    parts = [
        Paragraph("HAWKERBRIDGE / VERBATIM SCRIPT", style("label", 10, 13, ORANGE)),
        Paragraph("Three-minute narration", style("narration-title", 27, 33, FOREST)),
        Paragraph("Project owner: Shivam Gupta", style("name", 12, 17, MUTED)),
        Paragraph("Read the large text verbatim. Timing labels are not spoken. The current hosted demo uses a disclosed generic synthetic narrator. This script can also be read by Shivam. It describes the verified Databricks publication and the Firebase interface.", style("directions", 10, 14, MUTED)),
        Spacer(1, 10),
    ]
    for index, scene in enumerate(scenes):
        if index in (2, 4):
            parts.append(PageBreak())
        start, end = int(scene["start"]), int(scene["end"])
        timing = f"{start // 60}:{start % 60:02} to {end // 60}:{end % 60:02} / {labels[index]}"
        parts.append(Paragraph(escape(timing), style("timing", 9, 12, ORANGE, keepWithNext=True)))
        parts.append(Paragraph(escape(scene["text"]), style("spoken", 16, 23)))
        parts.append(Spacer(1, 16))
    SimpleDocTemplate(
        str(OUTPUT / "hawkerbridge-video-narration.pdf"), pagesize=A4,
        topMargin=40, bottomMargin=55, leftMargin=51, rightMargin=51,
        title="HawkerBridge - Verbatim video narration", author="Shivam Gupta",
    ).build(parts, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build_concept()
    build_narration()
