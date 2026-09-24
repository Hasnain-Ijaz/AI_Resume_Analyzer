import os
import io
import json
import re
import traceback
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document
from groq import Groq

from prompts import RESUME_EXTRACTION_PROMPT, JD_EXTRACTION_PROMPT, ANALYSIS_PROMPT
from report_generator import build_pdf_report

load_dotenv()

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")

DEFAULT_MODEL = "openai/gpt-oss-120b"


def get_setting(name, default=None):
    value = os.getenv(name)
    if value:
        return value
    try:
        if name in st.secrets:
            value = st.secrets[name]
            if value:
                return str(value)
    except Exception:
        pass
    return default


def get_api_key():
    return get_setting("GROQ_API_KEY") or get_setting("AI_API_KEY")


def get_model():
    return get_setting("MODEL_NAME", DEFAULT_MODEL)


def get_client():
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Add it to .env or Streamlit Cloud Secrets."
        )
    if api_key.startswith("gsk_your_") or api_key in {
        "your_groq_api_key_here",
        "YOUR_GROQ_API_KEY",
    }:
        raise RuntimeError("A placeholder API key is being used. Add your real Groq API key.")
    return Groq(api_key=api_key)


def clean_json_text(text):
    if not text:
        raise ValueError("The AI returned an empty response.")
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError("The AI returned a response that was not valid JSON.")


def call_json(prompt, model=None):
    client = get_client()
    model = model or get_model()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional ATS and resume analysis assistant. "
                "Follow the requested JSON structure exactly. Return valid JSON only."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=messages,
        )
    except Exception as first_error:
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=messages,
            )
        except Exception:
            raise first_error

    return clean_json_text(response.choices[0].message.content)


def extract_pdf_text(uploaded_file):
    uploaded_file.seek(0)
    reader = PdfReader(uploaded_file)
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if not text:
        raise ValueError(
            "No readable text was found in the PDF. If it is a scanned/image PDF, use OCR first."
        )
    return text


def extract_docx_text(uploaded_file):
    uploaded_file.seek(0)
    document = Document(uploaded_file)
    text = "\n".join(
        p.text.strip() for p in document.paragraphs if p.text.strip()
    ).strip()
    if not text:
        raise ValueError("No readable text was found in the DOCX file.")
    return text


def extract_resume_text(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(uploaded_file)
    if suffix == ".docx":
        return extract_docx_text(uploaded_file)
    raise ValueError("Unsupported file type. Please upload a PDF or DOCX resume.")


def safe_error_message(error):
    return re.sub(r"gsk_[A-Za-z0-9_-]+", "gsk_***REDACTED***", str(error))


def run_analysis(resume_text, job_description, model):
    progress = st.progress(0, text="Preparing resume analysis...")

    # Step 1: Resume extraction
    progress.progress(15, text="Extracting resume information...")

    resume_prompt = RESUME_EXTRACTION_PROMPT.replace(
        "{resume_text}",
        resume_text
    )

    resume_data = call_json(
        resume_prompt,
        model
    )

    # Step 2: Job description extraction
    progress.progress(35, text="Analyzing the job description...")

    jd_prompt = JD_EXTRACTION_PROMPT.replace(
        "{job_description}",
        job_description
    )

    jd_data = call_json(
        jd_prompt,
        model
    )

    # Step 3: Resume vs Job Description analysis
    progress.progress(
        55,
        text="Comparing resume with job requirements..."
    )

    analysis_prompt = (
        ANALYSIS_PROMPT
        .replace("{resume_text}", resume_text)
        .replace("{job_description}", job_description)
        .replace(
            "{resume_json}",
            json.dumps(
                resume_data,
                ensure_ascii=False,
                indent=2
            )
        )
        .replace(
            "{jd_json}",
            json.dumps(
                jd_data,
                ensure_ascii=False,
                indent=2
            )
        )
    )

    analysis = call_json(
        analysis_prompt,
        model
    )

    progress.progress(
        85,
        text="Preparing final report..."
    )

    result = {
        "resume_data": resume_data,
        "jd_data": jd_data,
        "analysis": analysis,
        "model": model,
    }

    progress.progress(
        100,
        text="Analysis completed."
    )

    return result


def render_list(items, empty_message="No items available."):
    if not items:
        st.info(empty_message)
        return
    for item in items:
        if isinstance(item, dict):
            title = item.get("title") or item.get("name") or item.get("skill")
            description = (
                item.get("description")
                or item.get("reason")
                or item.get("details")
                or item.get("text")
            )
            if title and description:
                st.markdown(f"**{title}** — {description}")
            elif title:
                st.markdown(f"• {title}")
            else:
                st.markdown(f"• {json.dumps(item, ensure_ascii=False)}")
        else:
            st.markdown(f"• {item}")


def render_analysis(result):
    analysis = result.get("analysis", {})

   def score(*values):
    for value in values:
        if value is not None:
            try:
                return max(0, min(100, int(float(value))))
            except (TypeError, ValueError):
                pass
    return 0

    scores = analysis.get("scores", {})

match_score = score(
    scores.get("overall_match"),
    analysis.get("match_score"),
    analysis.get("overall_match_score")
)

ats_score = score(
    scores.get("ats_compatibility"),
    analysis.get("ats_score")
)

keyword_score = score(
    scores.get("keyword_match"),
    analysis.get("keyword_score")
)

    st.subheader("📊 Resume Match Score")
    c1, c2, c3 = st.columns(3)
    c1.metric("Match Score", f"{match_score}%")
    c2.metric("ATS Score", f"{ats_score}%")
    c3.metric("Keyword Score", f"{keyword_score}%")
    st.progress(match_score / 100)

    tabs = st.tabs([
        "🎯 Summary", "💪 Strengths", "⚠️ Gaps", "🔑 Keywords",
        "🛠️ Improvements", "✍️ Tailored Bullets", "📋 Full JSON"
    ])

    with tabs[0]:
        st.markdown("### Recruiter Summary")
        st.write(analysis.get("recruiter_summary") or analysis.get("summary") or "No summary returned.")
        st.markdown("### Elevator Pitch")
        st.write(analysis.get("elevator_pitch") or "No elevator pitch returned.")

    with tabs[1]:
        st.markdown("### Resume Strengths")
        render_list(analysis.get("strengths"), "No strengths were returned.")

    with tabs[2]:
        st.markdown("### Skill / Experience Gaps")
        render_list(
            analysis.get("skill_gaps") or analysis.get("gaps") or analysis.get("missing_skills"),
            "No major gaps were returned.",
        )

    with tabs[3]:
    keywords = analysis.get("keywords", {})

    st.markdown("### 🔑 Matching Keywords")
    render_list(
        keywords.get("matched", []),
        "No matching keywords were returned.",
    )

    st.markdown("### ❌ Missing Keywords")
    render_list(
        keywords.get("missing", []),
        "No missing keywords were returned.",
    )

    st.markdown("### 🟡 Partial Keywords")
    render_list(
        keywords.get("partial", []),
        "No partial keywords were returned.",
    )

    with tabs[4]:
        st.markdown("### Resume Improvement Suggestions")
        render_list(
            analysis.get("improvements") or analysis.get("recommendations") or analysis.get("suggestions"),
            "No improvement suggestions were returned.",
        )

    with tabs[5]:
        st.markdown("### Tailored Bullet Points")
        render_list(
            analysis.get("tailored_bullets") or analysis.get("improved_bullets") or analysis.get("bullet_points"),
            "No tailored bullets were returned.",
        )

    with tabs[6]:
        st.json(result)


def main():
    st.title("📄 AI Resume Analyzer")
    st.caption("Upload your resume, paste a job description, and get an AI-powered ATS analysis.")

    with st.sidebar:
        st.header("⚙️ Configuration")
        model = get_model()
        st.text_input("AI Model", value=model, disabled=True)
        st.info("API key is read from GROQ_API_KEY in .env or Streamlit Cloud Secrets.")

        if st.button("🔌 Test AI Connection", use_container_width=True):
            try:
                client = get_client()
                response = client.chat.completions.create(
                    model=model,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": 'Return exactly this JSON: {"ok": true}',
                    }],
                    response_format={"type": "json_object"},
                )
                clean_json_text(response.choices[0].message.content)
                st.success("AI connection is working.")
            except Exception as e:
                st.error(
                    "AI connection failed:\n\n"
                    f"{type(e).__name__}: {safe_error_message(e)}"
                )

    st.markdown("### 1️⃣ Upload Resume")
    uploaded_file = st.file_uploader(
        "Upload PDF or DOCX", type=["pdf", "docx"]
    )

    st.markdown("### 2️⃣ Add Job Description")
    job_description = st.text_area(
        "Paste the complete job description here",
        height=280,
        placeholder="Paste the job description...",
    )

    use_sample = st.checkbox("Use sample resume/JD for testing")

    sample_resume = """
Hasnain Ijaz
MERN Stack Developer

Skills:
HTML, CSS, JavaScript, Bootstrap, React.js, Node.js, Express.js,
MongoDB, Firebase, Git, GitHub, REST APIs

Experience:
MERN Stack Trainee — CodSoft Software House
Worked on React applications, REST APIs, CRUD operations,
authentication, deployment, and responsive UI development.

Education:
BS Information Technology
University of Agriculture Faisalabad
"""

    sample_jd = """
We are looking for a Junior MERN Stack Developer.

Requirements:
- Strong JavaScript fundamentals
- React.js experience
- Node.js and Express.js
- MongoDB
- REST API development
- Git and GitHub
- Responsive web development
- Good problem-solving and communication skills
"""

    if use_sample:
        st.info("Sample data mode is enabled.")
        resume_text, jd_text = sample_resume, sample_jd
    else:
        resume_text, jd_text = None, job_description.strip()
        if uploaded_file is not None:
            try:
                resume_text = extract_resume_text(uploaded_file)
            except Exception as e:
                st.error(
                    "Resume parsing failed:\n\n"
                    f"{type(e).__name__}: {safe_error_message(e)}"
                )

    if st.button("🚀 Analyze Resume", type="primary", use_container_width=True):
        if not resume_text:
            st.warning("Please upload a PDF/DOCX resume or enable sample data.")
            return
        if not jd_text:
            st.warning("Please paste a job description.")
            return

        try:
            result = run_analysis(resume_text, jd_text, model)
            st.session_state["analysis_result"] = result
            st.success("✅ Resume analysis completed successfully.")
        except Exception as e:
            st.error("❌ Analysis failed. The exact technical error is shown below:")
            st.code(
                f"{type(e).__name__}: {safe_error_message(e)}",
                language="text",
            )
            with st.expander("Technical details"):
                st.code(traceback.format_exc(), language="text")
            st.info(
                "If you are using Streamlit Cloud, confirm GROQ_API_KEY and "
                "MODEL_NAME under Settings → Secrets."
            )

    result = st.session_state.get("analysis_result")
    if result:
        st.divider()
        render_analysis(result)
        st.divider()
        st.subheader("📥 Download Report")
        try:
            pdf_bytes = build_pdf_report(result)
            st.download_button(
                "Download PDF Report",
                data=pdf_bytes,
                file_name="resume_analysis_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.warning(
                "Analysis completed, but PDF generation failed: "
                f"{type(e).__name__}: {safe_error_message(e)}"
            )


if __name__ == "__main__":
    main()
