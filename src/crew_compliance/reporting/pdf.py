from __future__ import annotations

import io
import json

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from crew_compliance.domain.models import AnalysisResult, Finding
from crew_compliance.reporting.export import DISCLAIMER, period_label

NAVY = colors.HexColor("#1F3A5F")
INK = colors.HexColor("#1A1A1A")
MUTED = colors.HexColor("#5C6570")
RULE = colors.HexColor("#D6D0C4")


def export_pdf(
    result: AnalysisResult,
    *,
    company_name: str = "",
    logo_bytes: bytes | None = None,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Crew Compliance Checker — Screening Report",
        author=company_name or "Crew Compliance Checker",
    )
    doc.pageCompression = 0
    styles = _styles()
    story: list = []
    story.extend(_header(company_name, logo_bytes, styles))
    story.append(Paragraph("Executive summary", styles["section"]))
    story.append(_kpi_table(result, styles))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(DISCLAIMER, styles["disclaimer"]))
    story.append(PageBreak())
    story.append(Paragraph("Detailed findings", styles["section"]))
    if not result.findings:
        story.append(Paragraph("No findings were generated for this roster.", styles["body"]))
    else:
        for finding in result.findings:
            story.append(KeepTogether(_finding_block(finding, styles)))
            story.append(Spacer(1, 4 * mm))
    doc.build(story)
    return buf.getvalue()


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "brand",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=16,
            textColor=NAVY,
            leading=20,
        ),
        "sub": ParagraphStyle(
            "sub",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=9,
            textColor=MUTED,
            leading=12,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=13,
            textColor=NAVY,
            spaceBefore=2 * mm,
            spaceAfter=4 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=9,
            textColor=INK,
            leading=12,
            alignment=TA_JUSTIFY,
        ),
        "meta": ParagraphStyle(
            "meta",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            textColor=INK,
            leading=11,
            alignment=TA_LEFT,
        ),
        "label": ParagraphStyle(
            "label",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=8,
            textColor=MUTED,
            leading=10,
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=8,
            textColor=MUTED,
            leading=11,
            alignment=TA_JUSTIFY,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=11,
            textColor=INK,
            leading=14,
            spaceAfter=2 * mm,
        ),
    }


def _header(company_name: str, logo_bytes: bytes | None, styles: dict) -> list:
    brand = Paragraph(company_name.strip() or "Crew Compliance Checker", styles["brand"])
    subtitle = Paragraph("FTL and credential screening report", styles["sub"])
    if logo_bytes:
        try:
            reader = ImageReader(io.BytesIO(logo_bytes))
            iw, ih = reader.getSize()
            height = 16 * mm
            width = height * (iw / ih) if ih else height
            img = Image(reader, width=min(width, 32 * mm), height=height)
            inner = Table([[brand], [subtitle]])
            inner.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
            table = Table([[img, inner]], colWidths=[36 * mm, 146 * mm])
            table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            return [table, Spacer(1, 6 * mm)]
        except Exception:
            pass
    return [brand, subtitle, Spacer(1, 6 * mm)]


def _kpi_table(result: AnalysisResult, styles: dict) -> Table:
    counts = result.counts_by_severity()
    rows = [
        [_cell("Rule set", styles), _cell(f"{result.framework_name} · {result.ruleset_id} {result.ruleset_version}", styles)],
        [_cell("Date range screened", styles), _cell(period_label(result), styles)],
        [_cell("Roster", styles), _cell(result.source_name, styles)],
        [_cell("Potential findings", styles), _cell(str(result.potential_issue_count()), styles)],
        [_cell("Insufficient-data flags", styles), _cell(str(result.insufficient_data_count()), styles)],
        [
            _cell("Findings by severity", styles),
            _cell(
                f"Critical {counts['critical']} · High {counts['high']} · "
                f"Medium {counts['medium']} · Low {counts['low']}",
                styles,
            ),
        ],
        [_cell("Crew / duties / flights", styles), _cell(f"{result.crew_reviewed} / {result.duties_analyzed} / {result.flights_analyzed}", styles)],
    ]
    table = Table(rows, colWidths=[48 * mm, 134 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F1EA")),
                ("BOX", (0, 0), (-1, -1), 0.4, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _cell(text: str, styles: dict) -> Paragraph:
    return Paragraph(_escape(text), styles["meta"])


def _finding_block(finding: Finding, styles: dict) -> list:
    actual = "—" if finding.actual is None else f"{finding.actual} {finding.units}"
    required = "—" if finding.required is None else f"{finding.required} {finding.units}"
    evidence = json.dumps(finding.evidence, default=str, ensure_ascii=True)
    header = (
        f"{finding.severity.value.upper()} · {finding.kind.value.replace('_', ' ')} · "
        f"{finding.crew_name} ({finding.crew_id})"
    )
    body = [
        Paragraph(_escape(header), styles["label"]),
        Paragraph(_escape(finding.rule_name), styles["title"]),
        Paragraph(_escape(finding.citation), styles["sub"]),
        Paragraph(_escape(finding.explanation), styles["body"]),
        Spacer(1, 2 * mm),
        _detail_table(
            [
                ("Actual vs required", f"{actual}  /  {required}  (difference {finding.difference})"),
                ("Evidence", evidence),
                ("Assumptions", " | ".join(finding.assumptions) or "—"),
                ("Limitations", " | ".join(finding.limitations) or "—"),
            ],
            styles,
        ),
    ]
    return body


def _detail_table(rows: list[tuple[str, str]], styles: dict) -> Table:
    data = [[Paragraph(_escape(label), styles["label"]), Paragraph(_escape(value), styles["meta"])] for label, value in rows]
    table = Table(data, colWidths=[38 * mm, 144 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.3, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.2, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
