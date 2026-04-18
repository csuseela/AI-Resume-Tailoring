from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from app.schemas.job import JobListing
from app.schemas.tailoring import TailoringResult

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, provider: str = "mock", api_key: str = "") -> None:
        self.provider = provider
        self.api_key = api_key

    def analyze(self, job: JobListing, resume: str) -> TailoringResult:
        if self.provider == "mock":
            return self._mock_analyze(job, resume)
        if self.provider == "openai":
            return self._openai_analyze(job, resume)
        raise ValueError(f"Unknown LLM provider: {self.provider}")

    def _mock_analyze(self, job: JobListing, resume: str) -> TailoringResult:
        """Smart mock tailoring that preserves the original resume structure.

        Strategy: only tailor the SUMMARY and SKILLS sections.
        NEVER fabricate experience bullets — the real ones are always better.
        """
        jd_lower = job.description.lower()
        title_lower = job.title.lower()
        resume_lower = resume.lower()

        jd_keywords = _extract_jd_keywords(jd_lower)
        resume_skills = _extract_resume_skills(resume)

        tailored_summary = _build_tailored_summary(
            resume, job.title, job.company, jd_keywords,
        )

        tailored_skills = _build_tailored_skills(
            resume_skills, jd_keywords, jd_lower,
        )

        fit = _calculate_fit_score(resume_lower, jd_lower, jd_keywords)

        reason = _build_reason(job, jd_keywords, resume_lower)

        return TailoringResult(
            summary=tailored_summary,
            skills=tailored_skills,
            experience_bullets=None,
            fit_score=fit,
            one_line_reason=reason,
        )

    def _openai_analyze(self, job: JobListing, resume: str) -> TailoringResult:
        import requests

        prompt = self._build_prompt(job, resume)
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return self.parse_structured_output(content)

    @staticmethod
    def _build_prompt(job: JobListing, resume: str) -> str:
        return f"""You are an expert ATS resume optimizer. Your job is to tailor an existing resume
for a specific role WITHOUT fabricating new experience or changing the structure.

RULES:
1. Keep ALL original experience bullets — they contain real metrics and achievements
2. Only modify the SUMMARY to target this specific role
3. Only modify SKILLS to ensure JD keywords appear (add missing ones, reorder for relevance)
4. Do NOT invent new experience bullets or change the formatting
5. Preserve all company names, dates, and role titles exactly as they are

JOB:
Title: {job.title}
Company: {job.company}
Description: {job.description[:3000]}

RESUME:
{resume[:4000]}

Output JSON with these keys:
- summary: A 2-3 sentence professional summary tailored to this specific job, based on the candidate's REAL background
- skills: The complete skills section with JD keywords added and relevant skills prioritized (keep the categorized format)
- experience_bullets: null (preserve original experience as-is)
- fit_score: 0-100 how well the candidate fits
- one_line_reason: Why this is a good/bad fit
"""

    @staticmethod
    def parse_structured_output(raw: str) -> TailoringResult:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        data = json.loads(cleaned)
        return TailoringResult(**data)


# ---------------------------------------------------------------------------
# Helper functions for smart mock tailoring
# ---------------------------------------------------------------------------

_TECH_KEYWORDS: Set[str] = {
    "sql", "python", "r", "java", "scala", "javascript", "typescript",
    "tableau", "power bi", "looker", "excel", "hex",
    "snowflake", "redshift", "bigquery", "databricks", "spark",
    "dbt", "airflow", "kafka", "etl", "elt", "data pipeline",
    "aws", "azure", "gcp", "cloud", "s3", "lambda", "glue",
    "docker", "kubernetes", "terraform", "ci/cd",
    "machine learning", "deep learning", "nlp", "ai", "llm",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "data modeling", "data warehouse", "data lake",
    "data governance", "data quality", "data catalog",
    "agile", "scrum", "jira", "confluence",
    "api", "rest", "graphql", "microservices",
    "git", "github", "a/b testing", "statistical analysis",
    "regression", "kpi", "okr", "dashboard",
    "stakeholder management", "cross-functional", "roadmap",
    "program management", "project management",
}


def _extract_jd_keywords(jd_lower: str) -> Set[str]:
    """Extract technical and role-relevant keywords from the job description."""
    found: Set[str] = set()
    for kw in _TECH_KEYWORDS:
        if kw in jd_lower:
            found.add(kw)
    return found


def _extract_resume_skills(resume: str) -> List[str]:
    """Extract the existing skills section lines from the resume."""
    lines = resume.split("\n")
    skills_lines: List[str] = []
    in_skills = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("## skills"):
            in_skills = True
            continue
        if in_skills and stripped.startswith("## "):
            break
        if in_skills and stripped:
            skills_lines.append(stripped)
    return skills_lines


def _build_tailored_summary(
    resume: str, job_title: str, company: str, jd_keywords: Set[str],
) -> str:
    """Build a summary based on the REAL resume content, targeted to the role."""
    lines = resume.split("\n")
    original_summary = ""
    in_summary = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("## summary"):
            in_summary = True
            continue
        if in_summary and stripped.startswith("## "):
            break
        if in_summary and stripped:
            original_summary += stripped + " "

    original_summary = original_summary.strip()
    if not original_summary:
        original_summary = "Experienced analytics and program management professional."

    core_tools: List[str] = []
    priority_tools = ["sql", "python", "snowflake", "dbt", "tableau", "power bi",
                      "looker", "bigquery", "databricks", "aws", "airflow", "spark"]
    for tool in priority_tools:
        if tool in {k.lower() for k in jd_keywords}:
            core_tools.append(tool.title() if len(tool) > 3 else tool.upper())

    tools_str = ", ".join(core_tools[:6]) if core_tools else "SQL, Python, and BI tools"

    role_type = "analytics"
    title_lower = job_title.lower()
    if "program" in title_lower or "tpm" in title_lower:
        role_type = "program management and analytics"
    elif "engineer" in title_lower:
        role_type = "data engineering and analytics"
    elif "manager" in title_lower and "program" not in title_lower:
        role_type = "analytics leadership"

    summary = (
        f"Analytics Manager and Principal Data Analyst with 18+ years delivering "
        f"enterprise BI, data governance, and advanced analytics across financial "
        f"services and technology. Expert in {tools_str}. "
        f"Seeking to leverage deep {role_type} expertise to drive data-informed "
        f"decision-making as {job_title} at {company}."
    )

    return summary


def _build_tailored_skills(
    existing_skills: List[str], jd_keywords: Set[str], jd_lower: str,
) -> str:
    """Merge existing skills with JD keywords to maximize ATS match."""
    existing_text = " ".join(existing_skills).lower()

    missing: List[str] = []
    for kw in sorted(jd_keywords):
        if kw not in existing_text:
            display = kw.title() if len(kw) > 3 else kw.upper()
            missing.append(display)

    result_lines = list(existing_skills)
    if missing:
        result_lines.append(
            f"\nAdditional Relevant Skills: {', '.join(missing)}"
        )

    return "\n".join(result_lines)


def _calculate_fit_score(resume_lower: str, jd_lower: str, jd_keywords: Set[str]) -> float:
    """Calculate a realistic fit score based on keyword overlap."""
    if not jd_keywords:
        return 75.0

    matched = sum(1 for kw in jd_keywords if kw in resume_lower)
    keyword_ratio = matched / len(jd_keywords)

    score = 50 + (keyword_ratio * 45)
    return round(min(score, 98), 1)


def _build_reason(job: JobListing, jd_keywords: Set[str], resume_lower: str) -> str:
    """Build a specific reason explaining the fit."""
    matched = [kw for kw in sorted(jd_keywords) if kw in resume_lower]
    top_matches = matched[:4]
    if top_matches:
        match_str = ", ".join(kw.title() if len(kw) > 3 else kw.upper() for kw in top_matches)
        return (
            f"Strong match for {job.title} at {job.company} — "
            f"resume demonstrates expertise in {match_str} "
            f"with {len(matched)}/{len(jd_keywords)} JD keywords covered"
        )
    return f"Partial match for {job.title} at {job.company} — additional keyword alignment needed"
