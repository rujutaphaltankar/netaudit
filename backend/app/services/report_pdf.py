"""PDF report generation (ReportLab)."""
from __future__ import annotations

from datetime import timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.db.models import Audit
from app.rules.loader import load_catalog
from app.services.audit_service import sorted_findings

SEV_COLOR = {"critical": "#7f1d1d", "high": "#c2410c", "medium": "#b45309", "low": "#1d4ed8"}
GRADE_COLOR = {"A": "#15803d", "B": "#4d7c0f", "C": "#b45309", "D": "#c2410c", "F": "#b91c1c", "N/A": "#475569"}
STATUS_LABEL = {"fail": "FAIL", "pass": "PASS", "unknown": "UNKNOWN", "not_applicable": "N/A"}
VENDOR_LABEL = {"cisco_ios": "Cisco IOS", "juniper_junos": "Juniper Junos"}
INK, MUTED, LINE = colors.HexColor("#0f172a"), colors.HexColor("#64748b"), colors.HexColor("#cbd5e1")

LIMITATIONS = [
    "This report is based only on the uploaded configuration file; it does not test the live device, its software version, or its network exposure.",
    "A rule is PASS only when explicit evidence satisfies it. Missing or ambiguous evidence is reported as UNKNOWN and is never counted as compliant.",
    "The score covers only the rules evaluated; it is not a certification. Passing these rules does not demonstrate compliance with NIST, ISO/IEC 27001, CIS or any other framework.",
    "Framework references are an interpretation by the project authors and should be verified against the official documents.",
    "AI suggestions (if any) are advisory, were reviewed by a human, and never affect findings or the score.",
    "Secrets (passwords, keys, community strings) are redacted before storage; this report never contains them.",
]


def _t(text: object) -> str:
    """Escape for ReportLab markup and replace characters the built-in fonts cannot draw."""
    return escape(str(text)).encode("latin-1", "replace").decode("latin-1")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontSize=22, textColor=INK, alignment=0, spaceAfter=4),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=10, textColor=MUTED, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=14, textColor=INK, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=9.5, leading=13, textColor=INK),
        "small": ParagraphStyle("sm", parent=base["Normal"], fontSize=8.5, leading=11, textColor=MUTED),
        "mono": ParagraphStyle("m", parent=base["Code"], fontName="Courier", fontSize=8, leading=10, textColor=INK,
                               backColor=colors.HexColor("#f1f5f9"), borderPadding=4, spaceBefore=2, spaceAfter=4),
        "cell": ParagraphStyle("c", parent=base["Normal"], fontSize=9, leading=11, textColor=INK),
        "big": ParagraphStyle("big", parent=base["Normal"], fontSize=30, leading=34, alignment=TA_CENTER, textColor=INK),
        "mid": ParagraphStyle("mid", parent=base["Normal"], fontSize=17, leading=34, alignment=TA_CENTER, textColor=INK),
        "bigsub": ParagraphStyle("bigs", parent=base["Normal"], fontSize=8.5, alignment=TA_CENTER, textColor=MUTED),
    }


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "NetAudit - Network Security Compliance Report")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _finding_block(f, st) -> KeepTogether:
    sev = SEV_COLOR.get(f.severity, "#334155")
    head = Paragraph(f'<b>{_t(f.rule_id)}</b> &nbsp;{_t(f.title)} &nbsp;<font color="{sev}"><b>[{f.severity.upper()}]</b></font>',
                     st["body"])
    parts = [head, Paragraph(_t(f.message), st["small"])]
    if f.observed:
        parts.append(Paragraph(f"<b>Observed:</b> {_t(f.observed)}", st["small"]))
    if f.evidence:
        ev = "<br/>".join(f"L{e.get('line_number') or '?'}: {_t(e.get('text', ''))}" for e in f.evidence[:6])
        parts.append(Paragraph(ev, st["mono"]))
    if f.remediation:
        parts.append(Paragraph("<b>Recommended fix</b>", st["small"]))
        parts.append(Paragraph(_t(f.remediation).replace("\n", "<br/>").replace("  ", "&nbsp;&nbsp;"), st["mono"]))
    if f.references:
        refs = "; ".join(f"{_t(r['framework'])} {_t(r['control'])}" for r in f.references)
        parts.append(Paragraph(f"<i>References:</i> {refs}", st["small"]))
    parts.append(Spacer(1, 6))
    return KeepTogether(parts)


def build_report(audit: Audit) -> bytes:
    st = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title=f"NetAudit report - {audit.filename}", author="NetAudit")
    story: list = []
    grade_col = GRADE_COLOR.get(audit.grade, "#475569")
    findings = sorted_findings(audit)
    by = lambda s: [f for f in findings if f.status == s]  # noqa: E731

    story += [Paragraph("Network Security Compliance Report", st["title"]),
              Paragraph(f"Generated from audit #{audit.id} - {audit.created_at.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC", st["sub"])]

    meta = [["File", _t(audit.filename)], ["Vendor", _t(VENDOR_LABEL.get(audit.vendor, audit.vendor))],
            ["Hostname", _t(audit.hostname or "(not found)")], ["Lines / size", f"{audit.line_count} lines / {audit.size_bytes} bytes"],
            ["SHA-256", _t(audit.sha256)], ["Rule catalog / parser", f"v{_t(audit.catalog_version)} / v{_t(audit.parser_version)}"],
            ["Audited by", _t(audit.created_by.username if audit.created_by else "-")]]
    mt = Table([[Paragraph(f"<b>{k}</b>", st["small"]), Paragraph(v, st["cell"])] for k, v in meta], colWidths=[38 * mm, 128 * mm])
    mt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story += [mt, Spacer(1, 10)]

    score_txt = "N/A" if audit.score is None else f"{audit.score:.0f}"
    cards = [[Paragraph(f'<font color="{grade_col}"><b>{score_txt}</b></font>', st["big"]),
              Paragraph(f'<font color="{grade_col}"><b>{_t(audit.grade)}</b></font>', st["big"]),
              Paragraph(f"<b>{_t(audit.risk_level.upper())}</b>", st["mid"]),
              Paragraph(f"<b>{'N/A' if audit.coverage is None else f'{audit.coverage:.0f}%'}</b>", st["big"])],
             [Paragraph("Score (0-100)", st["bigsub"]), Paragraph("Grade", st["bigsub"]),
              Paragraph("Highest failed severity", st["bigsub"]), Paragraph("Evidence coverage", st["bigsub"])]]
    ct = Table(cards, colWidths=[41.5 * mm] * 4)
    ct.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                            ("TOPPADDING", (0, 0), (-1, 0), 10), ("BOTTOMPADDING", (0, 1), (-1, 1), 8)]))
    story += [ct, Spacer(1, 8)]

    sev = audit.summary.get("failed_by_severity", {})
    counts = [["Passed", "Failed", "Unknown", "Not applicable", "Critical", "High", "Medium", "Low"],
              [audit.passed, audit.failed, audit.unknown, audit.not_applicable,
               sev.get("critical", 0), sev.get("high", 0), sev.get("medium", 0), sev.get("low", 0)]]
    kt = Table(counts, colWidths=[20.75 * mm] * 8)
    kt.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold")]))
    story += [kt, Paragraph(
        "Score = weighted share of evaluated rules that passed (critical 10, high 7, medium 4, low 2). "
        "A failed critical rule caps the grade at D. UNKNOWN and N/A rules are excluded from the score.", st["small"])]

    story.append(Paragraph(f"Failed checks ({len(by('fail'))})", st["h2"]))
    story += [_finding_block(f, st) for f in by("fail")] or [Paragraph("No failed checks.", st["body"])]

    story.append(Paragraph(f"Unverified checks - insufficient evidence ({len(by('unknown'))})", st["h2"]))
    story += [_finding_block(f, st) for f in by("unknown")] or [Paragraph("None.", st["body"])]

    story.append(Paragraph(f"Passed checks ({len(by('pass'))})", st["h2"]))
    rows = [[Paragraph(_t(f.rule_id), st["cell"]), Paragraph(_t(f.title), st["cell"]),
             Paragraph(f.severity.capitalize(), st["cell"])] for f in by("pass")]
    if rows:
        pt = Table(rows, colWidths=[28 * mm, 112 * mm, 26 * mm])
        pt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(pt)
    na = by("not_applicable")
    if na:
        story.append(Paragraph("Not applicable: " + ", ".join(_t(f.rule_id) for f in na), st["small"]))

    approved = [m for m in audit.ai_mappings if m.status == "approved"]
    if approved:
        story.append(Paragraph("Human-approved suggestions for unrecognized commands (advisory)", st["h2"]))
        for m in approved:
            story.append(Paragraph(f"<font face='Courier'>{_t(m.command_text)}</font><br/>{_t(m.meaning)} "
                                   f"<i>[{_t(m.category)}, impact: {_t(m.security_impact)}, source: {_t(m.source)}]</i>", st["body"]))
            story.append(Spacer(1, 4))

    story += [PageBreak(), Paragraph("Limitations and disclaimer", st["h2"])]
    story += [Paragraph(f"&bull; {_t(x)}", st["body"]) for x in LIMITATIONS]
    story += [Spacer(1, 6), Paragraph(_t(load_catalog().disclaimer), st["small"])]

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
