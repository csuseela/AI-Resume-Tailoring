from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Dict, Optional

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
        title_lower = job.title.lower()
        desc_lower = job.description.lower()

        skills_map = {
            "data analyst": "SQL, Python, Tableau, Power BI, Excel, Snowflake, dbt, Data Modeling, ETL, Statistical Analysis, A/B Testing",
            "program manager": "Agile, Scrum, JIRA, Confluence, Roadmap Planning, Cross-functional Leadership, Stakeholder Management, Risk Mitigation, OKRs",
            "data engineer": "Python, SQL, Spark, Airflow, Snowflake, dbt, AWS, Kafka, Data Pipeline Architecture, ETL/ELT, Data Modeling",
            "analytics": "SQL, Python, Tableau, Power BI, Looker, Statistical Modeling, KPI Development, Data Storytelling, A/B Testing",
        }

        skills = "SQL, Python, Tableau, Data Analysis, Cross-functional Collaboration"
        for key, val in skills_map.items():
            if key in title_lower:
                skills = val
                break

        if "snowflake" in desc_lower:
            skills += ", Snowflake"
        if "aws" in desc_lower:
            skills += ", AWS (S3, Glue, Redshift)"
        if "dbt" in desc_lower:
            skills += ", dbt"
        if "spark" in desc_lower:
            skills += ", Apache Spark"

        summaries = [
            f"Results-driven analytics professional with 18+ years of experience, specializing in {job.title.split()[0].lower()} roles. Proven track record of building scalable data solutions and driving data-informed decision-making at {job.company}.",
            f"Seasoned data and program management leader with deep expertise in SQL, Python, and BI tooling. Seeking to leverage 18+ years of cross-functional experience to deliver impact as {job.title} at {job.company}.",
            f"Strategic analytics professional combining technical depth (SQL, Python, Snowflake) with program leadership experience. Eager to drive {job.company}'s data strategy and operational excellence.",
        ]

        bullet_templates = [
            f"Led cross-functional data initiatives aligning with {job.company}'s focus on {_extract_focus(desc_lower)}, resulting in 30%+ improvement in operational efficiency",
            f"Designed and deployed automated ETL pipelines and dashboards that reduced manual reporting by 60%, directly relevant to {job.title} responsibilities",
            f"Partnered with engineering, product, and business stakeholders to define KPIs and build analytics frameworks — core to the {job.title} role at {job.company}",
            f"Managed end-to-end program delivery using Agile/Scrum methodologies, tracking milestones via JIRA and Confluence across distributed teams",
            f"Built predictive models and statistical analyses that informed $10M+ in strategic decisions, supporting data-driven culture at enterprise scale",
        ]

        fit = random.uniform(72, 95)

        return TailoringResult(
            summary=random.choice(summaries),
            skills=skills,
            experience_bullets={"Professional Experience": random.sample(bullet_templates, min(4, len(bullet_templates)))},
            fit_score=round(fit, 1),
            one_line_reason=f"Strong alignment between candidate's analytics/PM background and {job.title} requirements at {job.company}",
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
        return f"""You are an expert resume tailor. Analyze this job and resume, then output a JSON object.

JOB:
Title: {job.title}
Company: {job.company}
Description: {job.description[:3000]}

RESUME:
{resume[:4000]}

Output JSON with these keys:
- summary: A 2-3 sentence professional summary tailored to this specific job
- skills: Comma-separated list of skills matching this job
- experience_bullets: Object with section name as key and array of 4 tailored bullet points
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


def _extract_focus(desc: str) -> str:
    focus_areas = {
        "data governance": "data governance and quality",
        "machine learning": "ML/AI and advanced analytics",
        "cloud": "cloud infrastructure and scalability",
        "compliance": "regulatory compliance and risk management",
        "analytics": "analytics and business intelligence",
        "pipeline": "data pipeline optimization",
        "dashboard": "reporting and dashboard development",
    }
    for keyword, focus in focus_areas.items():
        if keyword in desc:
            return focus
    return "data-driven decision-making"
