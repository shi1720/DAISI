"""Portable, auditable plan exports. All user text is escaped before PDF rendering."""

from __future__ import annotations

import csv
import io
import json
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def csv_cell(value):
    text = str(value)
    # Keep spreadsheet programs from executing untrusted note/title cells as formulae.
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def plan_csv(plan: dict) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["HawkerBridge planning proposal", csv_cell(plan["title"])])
    writer.writerow(["Date", plan["date"], "Status", plan["status"]])
    writer.writerow(
        ["Basis", "Assumed meals; candidate localities require venue/operator verification"]
    )
    writer.writerow(["Source fingerprint", plan["result"]["source_fingerprint"]])
    writer.writerow(["Model", plan["result"]["model_version"]])
    writer.writerow(["Notes", csv_cell(plan.get("notes", ""))])
    writer.writerow([])
    writer.writerow(
        [
            "Candidate locality",
            "Planning area",
            "Latitude",
            "Longitude",
            "Planned meals / day",
            "Cost SGD / day",
            "Served subzone IDs",
        ]
    )
    for site in plan["result"]["sites"]:
        writer.writerow(
            [
                csv_cell(site["name"]),
                csv_cell(site["planning_area"]),
                site["lat"],
                site["lng"],
                site["meals"],
                site["cost"],
                ";".join(site["covered_zone_ids"]),
            ]
        )
    writer.writerow([])
    writer.writerow(["Assumptions", json.dumps(plan["parameters"], sort_keys=True)])
    for item in plan["result"]["limitations"]:
        writer.writerow(["Limitation", csv_cell(item)])
    return output.getvalue().encode("utf-8-sig")


def plan_pdf(plan: dict) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=(210 * mm, 297 * mm),
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=19 * mm,
        title=plan["title"],
        author="HawkerBridge",
    )
    styles = getSampleStyleSheet()
    ink = colors.HexColor("#163e37")
    muted = colors.HexColor("#60736b")
    accent = colors.HexColor("#d35436")
    styles.add(
        ParagraphStyle(
            name="Brand", fontName="Helvetica-Bold", fontSize=11, textColor=ink, spaceAfter=16
        )
    )
    styles.add(
        ParagraphStyle(
            name="TitleHB",
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=29,
            textColor=ink,
            spaceAfter=11,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyHB",
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=ink,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallHB",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=muted,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeadingHB",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=ink,
            spaceBefore=13,
            spaceAfter=8,
        )
    )

    def p(t, style="BodyHB"):
        return Paragraph(escape(str(t)).replace("\n", "<br/>"), styles[style])

    result = plan["result"]
    summary = result["summary"]
    params = plan["parameters"]
    story = [
        p("H A W K E R B R I D G E   /   C O N T I N U I T Y   P L A N", "Brand"),
        p(plan["title"], "TitleHB"),
        p(
            f"{plan['date']}   |   {plan['status'].upper()}   |   One-day planning proposal",
            "SmallHB",
        ),
        p(
            "Proposed support requires verification of demand, accessible routes, a suitable venue and a licensed operator. No service has been booked or dispatched."
        ),
        Spacer(1, 5 * mm),
    ]
    kpis = [
        [
            p("ASSUMED MEALS / DAY", "SmallHB"),
            p("PLANNED COST / DAY", "SmallHB"),
            p("CANDIDATE LOCALITIES", "SmallHB"),
        ],
        [
            p(f"{summary['total_meals']:,}", "HeadingHB"),
            p(f"S${summary['spent']:,.2f}", "HeadingHB"),
            p(str(summary["sites_selected"]), "HeadingHB"),
        ],
    ]
    table = Table(kpis, colWidths=[58 * mm] * 3)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff3ec")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            table,
            p("Allocation rationale", "HeadingHB"),
            p(result["explanation"]),
            p("Proposed collection localities", "HeadingHB"),
        ]
    )
    rows = [[p(x, "SmallHB") for x in ["Locality / area", "Meals", "SGD / day"]]]
    for s in result["sites"]:
        rows.append(
            [p(s["name"] + "\n" + s["planning_area"]), p(str(s["meals"])), p(f"{s['cost']:,.2f}")]
        )
    if not result["sites"]:
        rows.append([p("No feasible support sites for these inputs."), p("0"), p("0.00")])
    tbl = Table(rows, colWidths=[110 * mm, 27 * mm, 37 * mm], repeatRows=1, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 1, ink),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#d9dfd5")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(tbl)
    story.extend(
        [
            p("Decision assumptions", "HeadingHB"),
            p(
                f"Budget S${params.get('budget', 1500):,.2f}/day. Setup S${params.get('site_cost', 300):,.2f}/site/day. "
                f"Meals S${params.get('meal_cost', 4):,.2f} each. Capacity {params.get('meals_per_site', 150)} meals/site/day. "
                f"Participation {params.get('participation_rate', 0.05):.1%} of census residents in flagged subzones. "
                f"Maximum {params.get('max_sites', 3)} sites. Reach {params.get('radius_m', 800)} m straight line. "
                f"Senior preference multiplier {params.get('senior_weight', 2):g}. These inputs are assumptions."
            ),
            p(
                f"Estimated demand under these assumptions: {summary['estimated_demand']:,} meals/day. "
                f"Unallocated demand: {summary['unmet_demand']:,}. Unspent budget: S${summary['unspent']:,.2f}. "
                f"Solver: {summary['solver_status']}."
            ),
        ]
    )
    if plan.get("notes"):
        story.extend([p("Coordinator notes", "HeadingHB"), p(plan["notes"])])
    story.extend(
        [
            p("Before implementation", "HeadingHB"),
            p(
                "Confirm actual resident demand and dietary needs. Secure accessible premises and permissions. Confirm an operator, staffing and safe food handling. Recheck official closure dates. Agree a contact, delivery schedule and a way to record uptake and unused meals."
            ),
        ]
    )
    story.extend([p("Evidence and limitations", "HeadingHB")])
    for limit in result["limitations"]:
        story.append(p(limit, "SmallHB"))
    story.extend(
        [
            p(f"Model: {result['model_version']}. Generated: {plan['updated_at']}.", "SmallHB"),
            p("Snapshot SHA256: " + result["source_fingerprint"], "SmallHB"),
            p(
                "Open-data references: data.gov.sg (NEA closure schedule, Census 2020 population, URA Master Plan 2019 boundaries). Full provenance is available in the app Evidence page and JSON export.",
                "SmallHB",
            ),
        ]
    )

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1)
        canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(muted)
        canvas.drawString(18 * mm, 10 * mm, "HawkerBridge / Human review required before action")
        canvas.drawRightString(192 * mm, 10 * mm, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
