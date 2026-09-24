RESUME_EXTRACTION_PROMPT = """
Extract structured information from the resume below.

Return JSON with exactly these broad keys:
{{
  "candidate": {{
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "portfolio": ""
  }},
  "summary": "",
  "education": [],
  "experience": [],
  "projects": [],
  "skills": [],
  "certifications": [],
  "languages": []
}}

Rules:
- Use only information present in the resume.
- If a field is absent, return an empty string or empty list.
- Do not infer missing experience or skills.
- Preserve important technical names.

RESUME:
{resume_text}
"""


JD_EXTRACTION_PROMPT = """
Extract structured requirements from the job description.

Return JSON:
{{
  "job_title": "",
  "required_skills": [],
  "preferred_skills": [],
  "responsibilities": [],
  "experience_requirements": [],
  "education_requirements": [],
  "certifications": [],
  "soft_skills": [],
  "keywords": []
}}

Rules:
- Use only information present in the job description.
- Do not add requirements that are not present.
- Distinguish required and preferred skills when the wording permits.

JOB DESCRIPTION:
{job_description}
"""


ANALYSIS_PROMPT = """
Analyze the candidate resume against the target job description.

You have:
1. Raw resume
2. Raw job description
3. Structured resume data
4. Structured job data

Return valid JSON using this schema:

{{
  "candidate": {{
    "name": "",
    "target_role": ""
  }},
  "scores": {{
    "overall_match": 0,
    "ats_compatibility": 0,
    "skills_match": 0,
    "keyword_match": 0,
    "experience_relevance": 0,
    "project_relevance": 0
  }},
  "keywords": {{
    "matched": [],
    "missing": [],
    "partial": []
  }},
  "strengths": [],
  "weaknesses": [],
  "skill_gaps": [
    {{
      "skill": "",
      "importance": "",
      "reason": ""
    }}
  ],
  "ats_analysis": {{
    "positive_factors": [],
    "risks": [],
    "recommendations": []
  }},
  "bullet_suggestions": [
    {{
      "original": "",
      "improved": "",
      "reason": ""
    }}
  ],
  "grammar_analysis": {{
    "issues": [],
    "weak_verbs": [],
    "suggestions": []
  }},
  "recruiter_summary": "",
  "elevator_pitch": "",
  "next_steps": []
}}

SCORING GUIDANCE:
- Scores must be integers from 0 to 100.
- Overall Match is an AI-assisted estimate, not a real ATS vendor score.
- Consider skills match, relevant experience, keywords, projects and ATS compatibility.
- Do not treat absence of a keyword as proof that the candidate has no such skill.
- Do not fabricate achievements or metrics.

BULLET SUGGESTION RULES:
- Only improve bullets that actually exist or are clearly supported by the resume.
- Never invent metrics, users, revenue, performance percentages, employers or responsibilities.
- If measurable impact is missing, tell the user where a real metric could be added.

GRAMMAR RULES:
- Identify vague wording, tense inconsistency, grammar issues and weak action verbs.
- Do not rewrite the entire resume.

PRIVACY/ACCURACY:
- Do not expose or repeat unnecessary personal information.
- Use "Not clearly demonstrated" when evidence is insufficient.

RAW RESUME:
{resume_text}

RAW JOB DESCRIPTION:
{job_description}

STRUCTURED RESUME:
{resume_json}

STRUCTURED JOB:
{jd_json}
"""
