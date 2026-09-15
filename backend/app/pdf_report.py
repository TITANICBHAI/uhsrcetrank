from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_report(result: dict, official_url: str) -> bytes:
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    data = result["data"]
    candidate = data["candidate"]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story = [
        Paragraph("UHSR CET 2026 — Estimated Merit Position Report", styles["Title"]),
        Paragraph("<b>UNOFFICIAL — ESTIMATED MERIT POSITION</b>", styles["Heading2"]),
        Paragraph("Independent Candidate Utility — Not an official UHSR document", styles["Normal"]),
        Spacer(1, 8),
        Table([
            ["Roll Number", candidate.get("roll_number") or "Not published"],
            ["Name", candidate.get("name") or "Not published"],
            ["CET Examination", candidate.get("cet_exam") or "Not published"],
            ["CET Score", str(candidate.get("cet_score") or "Not published")],
            ["Percentile", str(candidate.get("percentile") or "Not published")],
            ["Category", candidate.get("category") or "Not published"],
        ], colWidths=[45 * mm, 115 * mm], style=TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8c8c8")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#d6e4f7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])),
        Spacer(1, 12),
        Paragraph("Estimated Merit Position", styles["Heading2"]),
        Paragraph(
            f"<font size='28'><b>{data.get('merit_position') or 'Unavailable'}</b></font>"
            f" of {data.get('total_candidates') or '—'} candidates",
            styles["Normal"],
        ),
        Paragraph(f"{data.get('candidates_ahead') or 0} candidates ahead", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Ranking explanation", styles["Heading2"]),
        Paragraph(data.get("ranking_method") or "Dataset-specific method", styles["Normal"]),
        Paragraph("Dataset version: " + str(data.get("dataset_version") or "Not published"), styles["Normal"]),
        Spacer(1, 10),
        Paragraph(
            f"<b>Official-result warning:</b> This is an independent estimate, not an official "
            f"UHSR result or scorecard. For counselling and document verification, use "
            f"<link href='{official_url}' color='#1a3a6e'>{official_url}</link>.",
            styles["Normal"],
        ),
    ]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawCentredString(
            A4[0] / 2, 10 * mm,
            f"UNOFFICIAL — ESTIMATED MERIT POSITION | Generated {timestamp} | Not an official UHSR scorecard.",
        )
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()