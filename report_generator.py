from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib import colors


def _text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


def build_pdf_report(result, resume_data=None, jd_data=None):
    resume_data = resume_data or {}
    jd_data = jd_data or {}

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="AI Resume Analysis Report",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], alignment=TA_CENTER, spaceAfter=10
    )
    heading = ParagraphStyle(
        "ReportHeading", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6
    )
    body = ParagraphStyle(
        "ReportBody", parent=styles["BodyText"], leading=14, spaceAfter=5
    )
    small = ParagraphStyle(
        "Small", parent=body, fontSize=8.5, leading=11
    )

    story = []
    story.append(Paragraph("AI Resume Analysis Report", title))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", small
    ))
    story.append(Spacer(1, 8))

    candidate = result.get("candidate", {})
    story.append(Paragraph(
        f"Candidate: {_text(candidate.get('name') or resume_data.get('candidate', {}).get('name') or 'Not provided')}",
        body
    ))
    story.append(Paragraph(
        f"Target Role: {_text(result.get('target_role') or jd_data.get('job_title') or 'Not provided')}",
        body
    ))

    story.append(Paragraph("Score Summary", heading))
    scores = result.get("scores", {})
    score_rows = [["Metric", "Score"]]
    labels = [
        ("Overall Match", "overall_match"),
        ("ATS Compatibility", "ats_compatibility"),
        ("Skills Match", "skills_match"),
        ("Keyword Match", "keyword_match"),
        ("Experience Relevance", "experience_relevance"),
        ("Project Relevance", "project_relevance"),
    ]
    for label, key in labels:
        score_rows.append([label, _text(scores.get(key, 0)) + "/100"])

    table = Table(score_rows, colWidths=[95 * mm, 50 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    def add_list_section(title_text, items):
        story.append(Paragraph(title_text, heading))
        if not items:
            story.append(Paragraph("None identified.", body))
            return
        for item in items:
            if isinstance(item, dict):
                content = " — ".join(f"{k}: {_text(v)}" for k, v in item.items())
            else:
                content = _text(item)
            story.append(Paragraph("• " + content, body))

    keywords = result.get("keywords", {})
    add_list_section("Matched Keywords", keywords.get("matched", []))
    add_list_section("Missing Keywords", keywords.get("missing", []))
    add_list_section("Partial Matches", keywords.get("partial", []))
    add_list_section("Strengths", result.get("strengths", []))
    add_list_section("Areas to Improve", result.get("weaknesses", []))
    add_list_section("Skill Gaps", result.get("skill_gaps", []))

    ats = result.get("ats_analysis", {})
    add_list_section("ATS Positive Factors", ats.get("positive_factors", []))
    add_list_section("ATS Risks", ats.get("risks", []))
    add_list_section("ATS Recommendations", ats.get("recommendations", []))

    story.append(Paragraph("Tailored Bullet Suggestions", heading))
    suggestions = result.get("bullet_suggestions", [])
    if suggestions:
        for i, item in enumerate(suggestions, 1):
            if isinstance(item, dict):
                story.append(Paragraph(f"Suggestion {i}", styles["Heading3"]))
                story.append(Paragraph("Original: " + _text(item.get("original")), body))
                story.append(Paragraph("Improved: " + _text(item.get("improved")), body))
                story.append(Paragraph("Why: " + _text(item.get("reason")), body))
    else:
        story.append(Paragraph("No bullet suggestions returned.", body))

    grammar = result.get("grammar_analysis", {})
    add_list_section("Grammar / Clarity Issues", grammar.get("issues", []))
    add_list_section("Weak Action Verbs", grammar.get("weak_verbs", []))
    add_list_section("Grammar Suggestions", grammar.get("suggestions", []))

    story.append(Paragraph("Recruiter Summary", heading))
    story.append(Paragraph(_text(result.get("recruiter_summary")), body))

    story.append(Paragraph("Elevator Pitch", heading))
    story.append(Paragraph(_text(result.get("elevator_pitch")), body))

    add_list_section("Recommended Next Steps", result.get("next_steps", []))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Disclaimer: This report is AI-assisted. It does not guarantee ATS success, interviews, or employment. "
        "Verify every suggested change against your actual experience before using it.",
        small,
    ))

    doc.build(story)
    return buffer.getvalue()
