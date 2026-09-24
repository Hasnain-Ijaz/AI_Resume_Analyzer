# AI Resume Analyzer

An AI-powered Streamlit application that compares a resume against a target Job Description (JD) and produces structured, actionable feedback.

## Features

- PDF and DOCX resume upload
- Resume text extraction
- Job Description input
- AI-based resume and JD information extraction
- Keyword matching
- Matched / missing / partial keywords
- Resume match score
- ATS compatibility estimate
- Strengths and improvement areas
- Skill-gap analysis
- Tailored bullet-point suggestions
- Grammar and action-verb analysis
- Recruiter summary
- Elevator pitch
- Visual Streamlit dashboard
- Sample data loader
- Downloadable PDF analysis report
- Defensive error handling
- Environment-variable based API configuration

## AI Workflow

```text
Resume Upload
      |
      v
Resume Text Extraction
      |
      v
Resume Information Extraction
      |
      +----------------------+
                             |
Job Description ------------+
                             |
                             v
                   JD Requirement Extraction
                             |
                             v
                    Keyword / Skill Matching
                             |
                             v
                      ATS Analysis
                             |
                             v
                    AI Resume Analysis
                             |
             +---------------+---------------+
             |               |               |
             v               v               v
        Skill Gaps      Bullet Advice    Grammar
             |               |               |
             +---------------+---------------+
                             |
                             v
                    Recruiter Summary
                             |
                             v
                    Streamlit Dashboard
                             |
                             v
                       PDF Report
```

## Tech Stack

- Python
- Streamlit
- Groq API
- `openai/gpt-oss-120b` by default
- pypdf
- python-docx
- ReportLab
- python-dotenv

## Project Structure

```text
ai-resume-analyzer/
├── app.py
├── prompts.py
├── report_generator.py
├── requirements.txt
├── README.md
├── .gitignore
└── .env
```

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Configure API Key

Create `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=openai/gpt-oss-120b
```

Never commit a real API key to GitHub.

## 3. Run

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Google Colab

Install packages:

```python
!pip install -r requirements.txt
```

For a secret stored in Colab:

```python
from google.colab import userdata
import os

os.environ["GROQ_API_KEY"] = userdata.get("GROQ_API_KEY")
os.environ["MODEL_NAME"] = "openai/gpt-oss-120b"
```

For local development, `.env` is supported through `python-dotenv`.

## Streamlit Cloud Deployment

1. Create a GitHub repository.
2. Upload:
   - `app.py`
   - `prompts.py`
   - `report_generator.py`
   - `requirements.txt`
   - `README.md`
   - `.gitignore`
3. Do **not** upload a real `.env` file containing secrets.
4. Deploy the repository with Streamlit Community Cloud.
5. Open the Streamlit app's Secrets settings.
6. Add:

```toml
GROQ_API_KEY = "your_real_key"
MODEL_NAME = "openai/gpt-oss-120b"
```

7. Redeploy/restart the application.

## Testing Checklist

### Resume parser
- [ ] Valid PDF
- [ ] Valid DOCX
- [ ] Unsupported file
- [ ] Empty/scanned PDF
- [ ] Large file

### JD validation
- [ ] Empty JD
- [ ] Short JD
- [ ] Valid JD

### AI
- [ ] Valid API key
- [ ] Missing API key
- [ ] Invalid API key
- [ ] Rate limit
- [ ] Unexpected JSON

### Dashboard
- [ ] Scores
- [ ] Keywords
- [ ] ATS analysis
- [ ] Skill gaps
- [ ] Bullet suggestions
- [ ] Grammar analysis
- [ ] Recruiter summary

### Report
- [ ] PDF generation
- [ ] Download works

## Privacy

The app is designed to process resume content in memory where practical and does not intentionally save uploaded resumes to a database. AI processing sends the relevant resume/JD text to the configured AI provider, so users should review that provider's terms and privacy policy before using the app with sensitive information.

## Important AI Accuracy Rules

The workflow instructs the model not to invent:

- Experience
- Employers
- Skills
- Certifications
- Achievements
- Metrics
- Responsibilities

A missing keyword is not automatically treated as proof that a candidate lacks that skill.

The ATS score is an AI-assisted estimate based on common resume parsing considerations. It is not a score issued by a real ATS vendor and does not guarantee interview or employment outcomes.

## Future Improvements

- Resume rewriting mode
- Cover-letter generator
- Compare one resume against multiple JDs
- Resume version history
- RAG-powered career guidance
- Local/open-source model support
- Job application tracker
- LinkedIn profile analysis
