"""
pdf_export.py
=============
Generates a professional solar proposal PDF as raw bytes using ReportLab Platypus.
No Streamlit dependency — safe to import anywhere.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pkr(value) -> str:
    """Format a number as a comma-separated PKR string."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def generate_proposal_pdf(
    estimate: dict,
    explanation: str,
    mounting: dict,
    vendor_check: dict = None,
) -> bytes:
    """Generate a solar proposal PDF and return it as raw bytes.

    Args:
        estimate:     Dict from get_full_estimate() — system_kw, num_panels,
                      system_cost_pkr, monthly_savings_pkr, payback_years, etc.
        explanation:  Plain-language string from get_explanation().
        mounting:     Dict from get_mounting_recommendation() — structure_recommendation,
                      ip_rating, ip_reason.
        vendor_check: Optional dict with keys: verdict, honest_cost, vendor_price,
                      price_gap_pkr, price_gap_percent. Pass None if not used.

    Returns:
        PDF as raw bytes (never writes to disk).
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.85 * inch,
        leftMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )

    styles = getSampleStyleSheet()

    # ── Custom styles ──
    small_gray = ParagraphStyle(
        "SmallGray",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6b7280"),
        spaceAfter=4,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=colors.HexColor("#9ca3af"),
        fontName="Helvetica-Oblique",
        spaceBefore=20,
        borderPadding=(6, 0, 0, 0),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        spaceAfter=6,
    )

    story = []

    # ── Title ──
    story.append(Paragraph("Solar Advisor Bot — Honest Solar Proposal", styles["Title"]))
    today = datetime.now().strftime("%d %B %Y").lstrip("0")
    story.append(Paragraph(f"Generated on {today}", small_gray))
    story.append(Spacer(1, 0.25 * inch))

    # ── System Recommendation ──
    story.append(Paragraph("System Recommendation", styles["Heading2"]))

    metrics_data = [
        ["Metric", "Value"],
        ["System Size (kW)", str(estimate.get("system_kw", "—"))],
        ["Number of Panels", str(estimate.get("num_panels", "—"))],
        ["Estimated System Cost (PKR)", f"Rs. {_pkr(estimate.get('system_cost_pkr'))}"],
        ["Estimated Monthly Savings (PKR)", f"Rs. {_pkr(estimate.get('monthly_savings_pkr'))}"],
        ["Payback Period (years)", str(estimate.get("payback_years", "—"))],
    ]

    metrics_table = Table(
        metrics_data,
        colWidths=[3.2 * inch, 3.2 * inch],
        hAlign="LEFT",
    )
    metrics_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.black),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        # Data rows
        ("FONTSIZE",     (0, 1), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        # Grid
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.2 * inch))

    # ── What This Means For You ──
    story.append(Paragraph("What This Means For You", styles["Heading2"]))
    story.append(Paragraph(explanation or "No explanation available.", body_style))
    story.append(Spacer(1, 0.15 * inch))

    # ── Mounting & Protection ──
    story.append(Paragraph("Recommended Mounting & Protection", styles["Heading2"]))
    story.append(Paragraph(
        f"<b>Mounting structure:</b> {mounting.get('structure_recommendation', '—')}",
        body_style,
    ))
    story.append(Paragraph(
        f"<b>Inverter protection rating:</b> {mounting.get('ip_rating', '—')} — "
        f"{mounting.get('ip_reason', '—')}",
        body_style,
    ))
    story.append(Spacer(1, 0.15 * inch))

    # ── Vendor Quote Comparison (optional) ──
    if vendor_check is not None:
        story.append(Paragraph("Vendor Quote Comparison", styles["Heading2"]))

        verdict = str(vendor_check.get("verdict", "—"))
        gap_pct = vendor_check.get("price_gap_percent", 0)

        # Verdict cell colour
        if "FAIR" in verdict.upper():
            verdict_bg = colors.HexColor("#dcfce7")   # green
        elif "SLIGHTLY" in verdict.upper():
            verdict_bg = colors.HexColor("#fef3c7")   # amber
        else:
            verdict_bg = colors.HexColor("#fee2e2")   # red

        gap_sign = "+" if (vendor_check.get("price_gap_pkr", 0) or 0) >= 0 else ""

        vendor_data = [
            ["Honest Estimate (PKR)", "Vendor Price (PKR)", "Gap (PKR)", "Gap (%)", "Verdict"],
            [
                f"Rs. {_pkr(vendor_check.get('honest_cost'))}",
                f"Rs. {_pkr(vendor_check.get('vendor_price'))}",
                f"{gap_sign}Rs. {_pkr(vendor_check.get('price_gap_pkr'))}",
                f"{gap_sign}{gap_pct}%",
                verdict,
            ],
        ]

        vendor_table = Table(
            vendor_data,
            colWidths=[1.3 * inch, 1.3 * inch, 1.1 * inch, 0.8 * inch, 1.8 * inch],
            hAlign="LEFT",
        )
        vendor_table.setStyle(TableStyle([
            # Header
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            # Verdict cell coloured background
            ("BACKGROUND",    (4, 1), (4, 1), verdict_bg),
            ("FONTNAME",      (4, 1), (4, 1), "Helvetica-Bold"),
            # Data rows
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            # Grid
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(vendor_table)
        story.append(Spacer(1, 0.15 * inch))

    # ── Footer ──
    story.append(Paragraph(
        "All figures are calculated using real formulas based on IESCO tariff data "
        "(SRO 279(I)/2026) and standard solar industry parameters. This proposal "
        "does not use AI-generated numbers — only verified calculations.",
        footer_style,
    ))

    doc.build(story)
    return buffer.getvalue()
