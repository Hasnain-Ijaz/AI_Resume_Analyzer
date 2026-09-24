import os
import json
import re
import io
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document
from groq import Groq

from prompts import (
    RESUME_EXTRACTION_PROMPT,
    JD_EXTRACTION_PROMPT,
    ANALYSIS_PROMPT,
)
from report_generator import build_pdf_report

load_dotenv()

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown("""
<style>
.block-container {max-width: 1250px; padding-top: 2rem;}
.hero {
    padding: 1.6rem 1.8rem;
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 18px;
    margin-bottom: 1.2rem;
}
.hero h1 {margin-bottom: .25rem;}
.card {
    padding: 1rem;
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 14px;
    min-height: 110px;
}
.small-muted {opacity: .72; font-size: .9rem;}
.keyword {
    display: inline-block;
    padding: .28rem .55rem;
    margin: .2rem;
    border-radius: 999px;
    border: 1px solid rgba(128,128,128,.3);
    font-size: .86rem;
}
</style>
""", unsafe_allow_html=True)


# ---------- Helpers ----------
def extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def extract_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    # Include table text because many resumes use tables.
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                paragraphs.append(" | ".join(cells))
    return "\n".join(paragraphs).strip()


def extract_resume(file) -> str:
    data = file.getvalue()
    name = file.name.lower()
    if name.endswith(".pdf"):
        return extract_pdf(data)
    if name.endswith(".docx"):
        return extract_docx(data)
    raise ValueError("Unsupported file type. Please upload PDF or DOCX.")


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_client():
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("AI_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def call_json(prompt: str, model: str) -> dict:
    client = get_client()
    if client is None:
        raise RuntimeError("AI API key is not configured.")

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful resume-analysis AI. "
                    "Use only the supplied information. Never invent experience, "
                    "skills, employers, metrics, certifications, or achievements. "
                    "Return valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content
    return json.loads(content)


def safe_list(value):
    return value if isinstance(value, list) else []


def clamp_score(value):
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return 0


def score_breakdown(result):
    scores = result.get("scores", {})
    return {
        "Overall Match": clamp_score(scores.get("overall_match", 0)),
        "ATS Compatibility": clamp_score(scores.get("ats_compatibility", 0)),
        "Skills Match": clamp_score(scores.get("skills_match", 0)),
        "Keyword Match": clamp_score(scores.get("keyword_match", 0)),
        "Experience Relevance": clamp_score(scores.get("experience_relevance", 0)),
        "Project Relevance": clamp_score(scores.get("project_relevance", 0)),
    }


# ---------- Sample data ----------
SAMPLE_RESUME = """Alex Khan
Junior Full Stack Developer
alex.khan@example.com | Lahore, Pakistan | github.com/example

SUMMARY
Junior developer with hands-on experience building web applications using React,
JavaScript, Node.js, Express and MongoDB.

SKILLS
JavaScript, React, HTML, CSS, Bootstrap, Node.js, Express.js, MongoDB, REST APIs, Git, GitHub

EXPERIENCE
Web Development Intern — Example Software
Built reusable React components and integrated REST APIs.
Collaborated with developers to fix bugs and improve application features.

PROJECTS
Task Manager — React, Node.js, MongoDB
Developed a CRUD task management application with authentication and REST APIs.

E-commerce Store — MERN Stack
Built product listing, cart and authentication features.

EDUCATION
BS Information Technology
University
"""

SAMPLE_JD = """Junior MERN Stack Developer

We are looking for a Junior MERN Stack Developer to build and maintain modern web
applications.

Requirements:
- Strong JavaScript and React knowledge
- Node.js and Express.js
- MongoDB
- REST APIs
- Git and GitHub
- Understanding of TypeScript is preferred
- Familiarity with testing tools such as Jest is a plus
- Ability to work with a team and communicate effectively

Responsibilities:
- Build reusable frontend components
- Develop backend APIs
- Integrate databases
- Fix bugs and improve application performance
- Collaborate with other developers
"""


# ---------- Sidebar ----------
with st.sidebar:
    st.title("📄 AI Resume Analyzer")
    st.caption("Resume → JD → AI workflow → actionable feedback")
    st.divider()
    st.markdown("### Workflow")
    st.markdown(
        "1. Upload Resume\n"
        "2. Add Job Description\n"
        "3. Extract Resume & JD\n"
        "4. Match Skills & Keywords\n"
        "5. Run AI Analysis\n"
        "6. Review Dashboard\n"
        "7. Download Report"
    )
    st.divider()
    st.markdown("### Supported files")
    st.write("PDF and DOCX")
    st.caption("Your application should avoid permanently storing resume content.")

# ---------- Header ----------
st.markdown("""
<div class="hero">
<h1>📄 AI Resume Analyzer</h1>
<p>Analyze your resume against a specific job description and get structured,
actionable AI feedback for relevance, ATS compatibility, skills, keywords and
resume improvements.</p>
</div>
""", unsafe_allow_html=True)

# ---------- Inputs ----------
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Resume")
    uploaded = st.file_uploader(
        "Upload your PDF or DOCX resume",
        type=["pdf", "docx"],
        help="Maximum recommended size: 10 MB.",
    )
    if uploaded:
        size_mb = uploaded.size / (1024 * 1024)
        if size_mb > 10:
            st.error("File is larger than 10 MB. Please upload a smaller resume.")
            uploaded = None
        else:
            st.success(f"Uploaded: {uploaded.name}")

with col2:
    st.subheader("2. Job Description")
    jd_text = st.text_area(
        "Paste the target Job Description",
        height=260,
        placeholder="Paste the complete job description here...",
    )

sample_col1, sample_col2 = st.columns([1, 3])
with sample_col1:
    use_sample = st.button("🧪 Use Sample Data", use_container_width=True)
if use_sample:
    st.session_state["sample_resume"] = True
    st.session_state["sample_jd"] = SAMPLE_JD
    jd_text = SAMPLE_JD
    st.info("Sample JD loaded. Use the sample resume shown below as the demo resume.")

if st.session_state.get("sample_resume"):
    with st.expander("Sample Resume Preview", expanded=True):
        st.text(SAMPLE_RESUME)

st.divider()

analyze = st.button("🚀 Analyze Resume", type="primary", use_container_width=True)

# ---------- Analysis ----------
if analyze:
    if st.session_state.get("sample_resume"):
        resume_text = SAMPLE_RESUME
    elif not uploaded:
        st.error("Please upload a PDF or DOCX resume.")
        st.stop()
    else:
        try:
            resume_text = extract_resume(uploaded)
        except Exception:
            st.error("We could not read this file. Please upload a valid text-based PDF or DOCX.")
            st.stop()

    resume_text = clean_text(resume_text)
    jd_text = clean_text(jd_text)

    if len(resume_text) < 80:
        st.error("Not enough readable resume text was found. Please upload a text-based resume.")
        st.stop()

    if len(jd_text) < 100:
        st.error("Please provide a Job Description of at least 100 characters.")
        st.stop()

    model = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")

    if not get_client():
        st.error(
            "AI API key is not configured. Add GROQ_API_KEY to your .env file locally "
            "or Streamlit Secrets after deployment."
        )
        st.stop()

    progress = st.progress(0, text="Starting AI workflow...")

    try:
        progress.progress(15, text="Extracting structured resume information...")
        resume_data = call_json(
            RESUME_EXTRACTION_PROMPT.format(resume=resume_text[:30000]),
            model,
        )

        progress.progress(30, text="Extracting job requirements...")
        jd_data = call_json(
            JD_EXTRACTION_PROMPT.format(job_description=jd_text[:20000]),
            model,
        )

        progress.progress(50, text="Comparing skills, keywords and requirements...")
        analysis_prompt = ANALYSIS_PROMPT.format(
            resume=resume_text[:30000],
            job_description=jd_text[:20000],
            resume_json=json.dumps(resume_data, ensure_ascii=False),
            jd_json=json.dumps(jd_data, ensure_ascii=False),
        )
        result = call_json(analysis_prompt, model)

        progress.progress(85, text="Preparing recommendations...")
        result.setdefault("candidate", resume_data.get("candidate", {}))
        result.setdefault("target_role", jd_data.get("job_title", "Target Role"))
        result.setdefault("scores", {})
        result.setdefault("keywords", {})
        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("skill_gaps", [])
        result.setdefault("ats_analysis", {})
        result.setdefault("bullet_suggestions", [])
        result.setdefault("grammar_analysis", {})
        result.setdefault("recruiter_summary", "")
        result.setdefault("elevator_pitch", "")
        result.setdefault("next_steps", [])

        # Clamp scores to avoid invalid UI values.
        for k in list(result["scores"].keys()):
            result["scores"][k] = clamp_score(result["scores"][k])

        st.session_state["analysis_result"] = result
        st.session_state["resume_text"] = resume_text
        st.session_state["jd_text"] = jd_text
        st.session_state["resume_data"] = resume_data
        st.session_state["jd_data"] = jd_data
        progress.progress(100, text="Analysis complete.")
        st.success("Resume analysis completed successfully.")

   except Exception as e:
    progress.empty()

    error_message = str(e)

    st.error("❌ Analysis failed")

    with st.expander("🔍 Technical Error Details", expanded=True):
        st.code(error_message)

    st.info(
        "During development, the technical error is shown above so you can identify "
        "the exact API/model/configuration problem."
    )

# ---------- Results ----------
if "analysis_result" in st.session_state:
    result = st.session_state["analysis_result"]
    scores = score_breakdown(result)

    st.divider()
    st.header("📊 Analysis Dashboard")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Match", f"{scores['Overall Match']}/100")
    c2.metric("ATS Compatibility", f"{scores['ATS Compatibility']}/100")
    c3.metric("Skills Match", f"{scores['Skills Match']}/100")
    c4.metric("Keyword Match", f"{scores['Keyword Match']}/100")

    st.subheader("Score Breakdown")
    score_cols = st.columns(3)
    for idx, (name, value) in enumerate(scores.items()):
        if name == "Overall Match":
            continue
        with score_cols[idx % 3]:
            st.write(f"**{name} — {value}/100**")
            st.progress(value / 100)

    tabs = st.tabs([
        "Overview", "Skills & Keywords", "ATS Analysis", "Skill Gaps",
        "Bullet Improvements", "Grammar", "Recruiter Summary"
    ])

    with tabs[0]:
        st.subheader("Strengths")
        strengths = safe_list(result.get("strengths"))
        if strengths:
            for item in strengths:
                st.success(str(item))
        else:
            st.info("No specific strengths were returned.")

        st.subheader("Areas to Improve")
        weaknesses = safe_list(result.get("weaknesses"))
        if weaknesses:
            for item in weaknesses:
                st.warning(str(item))
        else:
            st.info("No specific improvement areas were returned.")

        st.subheader("Recommended Next Steps")
        for item in safe_list(result.get("next_steps")):
            st.write(f"• {item}")

    with tabs[1]:
        keywords = result.get("keywords", {})
        a, b, c = st.columns(3)
        with a:
            st.subheader("Matched")
            for x in safe_list(keywords.get("matched")):
                st.markdown(f'<span class="keyword">{x}</span>', unsafe_allow_html=True)
        with b:
            st.subheader("Missing")
            for x in safe_list(keywords.get("missing")):
                st.markdown(f'<span class="keyword">{x}</span>', unsafe_allow_html=True)
        with c:
            st.subheader("Partial")
            for x in safe_list(keywords.get("partial")):
                st.markdown(f'<span class="keyword">{x}</span>', unsafe_allow_html=True)

    with tabs[2]:
        ats = result.get("ats_analysis", {})
        st.metric("Estimated ATS Compatibility", f"{scores['ATS Compatibility']}/100")
        st.caption("This is an AI-assisted estimate based on common resume parsing practices; it does not guarantee ATS success.")
        st.subheader("Positive Factors")
        for item in safe_list(ats.get("positive_factors")):
            st.success(str(item))
        st.subheader("Potential Risks")
        for item in safe_list(ats.get("risks")):
            st.warning(str(item))
        st.subheader("Recommendations")
        for item in safe_list(ats.get("recommendations")):
            st.info(str(item))

    with tabs[3]:
        gaps = safe_list(result.get("skill_gaps"))
        if not gaps:
            st.info("No skill gaps were returned.")
        for gap in gaps:
            if isinstance(gap, dict):
                skill = gap.get("skill", "Skill")
                importance = gap.get("importance", "Not specified")
                reason = gap.get("reason", "")
                st.markdown(f"### {skill}")
                st.write(f"**Importance:** {importance}")
                st.write(reason)
            else:
                st.write(f"• {gap}")

    with tabs[4]:
        suggestions = safe_list(result.get("bullet_suggestions"))
        if not suggestions:
            st.info("No bullet suggestions were returned.")
        for i, item in enumerate(suggestions, 1):
            if isinstance(item, dict):
                st.markdown(f"### Suggestion {i}")
                st.write("**Original**")
                st.code(item.get("original", ""), language=None)
                st.write("**Improved**")
                st.success(item.get("improved", ""))
                st.write(f"**Why:** {item.get('reason', '')}")
            else:
                st.write(f"• {item}")

    with tabs[5]:
        grammar = result.get("grammar_analysis", {})
        st.subheader("Grammar / Clarity Issues")
        for item in safe_list(grammar.get("issues")):
            st.warning(str(item))
        st.subheader("Weak Action Verbs")
        for item in safe_list(grammar.get("weak_verbs")):
            st.write(f"• {item}")
        st.subheader("Suggested Improvements")
        for item in safe_list(grammar.get("suggestions")):
            st.info(str(item))

    with tabs[6]:
        st.subheader("Recruiter Summary")
        st.write(result.get("recruiter_summary", "No summary returned."))
        st.subheader("Elevator Pitch")
        st.info(result.get("elevator_pitch", "No elevator pitch returned."))

    st.divider()
    st.subheader("📥 Download Analysis Report")
    try:
        pdf_bytes = build_pdf_report(
            result=result,
            resume_data=st.session_state.get("resume_data", {}),
            jd_data=st.session_state.get("jd_data", {}),
        )
        st.download_button(
            "Download PDF Report",
            data=pdf_bytes,
            file_name="ai_resume_analysis_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception:
        st.warning("PDF report generation is unavailable. You can still use the dashboard results.")

    with st.expander("View extracted resume text"):
        st.text(st.session_state.get("resume_text", "")[:12000])

st.caption("AI-assisted analysis only. Always verify suggestions against your actual experience before editing your resume.")
