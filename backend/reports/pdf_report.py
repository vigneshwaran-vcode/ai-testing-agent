"""PDF Report Generator for AI Model Testing & Investigation."""
import io
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from database import get_session, get_session_results, get_capability_scores

def generate_pdf_report(session_id: int) -> bytes:
    """
    Builds a professional multi-page PDF evaluation report.
    """
    session = get_session(session_id)
    if not session:
        return b""

    results = get_session_results(session_id)
    cap_scores = get_capability_scores(session_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#4f46e5")  # Indigo/Purple
    secondary_color = colors.HexColor("#2563eb")  # Blue
    dark_color = colors.HexColor("#1e293b")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=primary_color,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=dark_color,
        spaceBefore=14,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=dark_color,
        leading=12
    )
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#475569"),
        leading=11
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("AI Model Testing, Evaluation & Investigation Report", title_style))
    story.append(Paragraph(f"Examining: <b>{session.get('provider', '').upper()} / {session.get('model_id', '')}</b> &nbsp;|&nbsp; Session: {session.get('session_name', '')} &nbsp;|&nbsp; Date: {session.get('started_at', '')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=14))

    # Summary Executive Card
    overall_score = session.get('overall_score', 0)
    rel_level = session.get('reliability_level', 'UNKNOWN')
    rel_color = "#16a34a" if rel_level == "HIGH" else ("#d97706" if rel_level == "MEDIUM" else "#dc2626")

    summary_data = [
        [
            Paragraph(f"<b>Overall Score:</b> <font color='{rel_color}' size='12'><b>{overall_score}/100</b></font>", body_style),
            Paragraph(f"<b>Reliability Level:</b> <font color='{rel_color}'><b>{rel_level}</b></font>", body_style),
            Paragraph(f"<b>Average Latency:</b> {session.get('avg_response_time', 0)} ms", body_style),
        ],
        [
            Paragraph(f"<b>Total Tests Executed:</b> {session.get('total_tests', 0)}", body_style),
            Paragraph(f"<b>Passed Tests:</b> <font color='#16a34a'><b>{session.get('passed_tests', 0)}</b></font>", body_style),
            Paragraph(f"<b>Failed / Issues:</b> <font color='#dc2626'><b>{session.get('failed_tests', 0)}</b></font>", body_style),
        ]
    ]
    sum_table = Table(summary_data, colWidths=[175, 175, 180])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 14))

    # Capability Breakdown Table
    if cap_scores:
        story.append(Paragraph("Capability Performance Breakdown", h2_style))
        cap_table_data = [["Capability", "Tests", "Avg Score", "Avg Latency", "Failures", "Reliability"]]
        for cs in cap_scores:
            c_score = cs.get("avg_score", 0)
            c_rel = cs.get("reliability_level", "LOW")
            cap_table_data.append([
                cs.get("capability", "").title(),
                str(cs.get("total_tests", 0)),
                f"{c_score}%",
                f"{cs.get('avg_response_time', 0)} ms",
                str(cs.get("failure_count", 0)),
                c_rel
            ])
        c_table = Table(cap_table_data, colWidths=[130, 60, 80, 90, 70, 100])
        c_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(c_table)
        story.append(Spacer(1, 14))

    # Individual Investigation Results
    story.append(Paragraph("Investigation & Failure Details", h2_style))
    for idx, r in enumerate(results, 1):
        status_color = "#16a34a" if r.get('score', 0) >= 80 else ("#d97706" if r.get('score', 0) >= 50 else "#dc2626")
        prompt_text = (r.get("prompt") or "")[:200] + ("..." if len(r.get("prompt") or "") > 200 else "")
        response_text = (r.get("model_response") or "")[:250] + ("..." if len(r.get("model_response") or "") > 250 else "")

        failures_str = ""
        try:
            raw_f = r.get("failures")
            if raw_f:
                parsed_f = json.loads(raw_f) if isinstance(raw_f, str) else raw_f
                failures_str = "; ".join(parsed_f) if isinstance(parsed_f, list) else str(parsed_f)
        except Exception:
            failures_str = str(r.get("failures", ""))

        test_card = [
            [
                Paragraph(f"<b>#{idx}. [{r.get('capability', '').upper()}] {r.get('subcategory', '')} ({r.get('difficulty', '')})</b>", body_style),
                Paragraph(f"<b>Score: <font color='{status_color}'>{r.get('score', 0)}/100</font></b> | Status: <b>{r.get('status', '')}</b>", small_style)
            ],
            [
                Paragraph(f"<b>Prompt:</b> {prompt_text}", small_style),
                Paragraph(f"<b>Latency:</b> {r.get('response_time_ms', 0)} ms | <b>Severity:</b> {r.get('severity', 'low')}", small_style)
            ],
            [
                Paragraph(f"<b>Model Output:</b> {response_text}", small_style),
                Paragraph(f"<b>Detected Issue:</b> {failures_str or 'None'}<br/><b>Recommendation:</b> {r.get('recommendation', 'N/A')}", small_style)
            ]
        ]
        card_table = Table(test_card, colWidths=[310, 220])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#e2e8f0")),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor("#f1f5f9")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(card_table)
        story.append(Spacer(1, 6))

    doc.build(story)
    return buffer.getvalue()
