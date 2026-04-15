"""ATS (Applicant Tracking System) resume-to-job match scorer.

Scoring methodology:
  1. Hard-skill keyword match (40%)
  2. Soft-skill keyword match (10%)
  3. Job title alignment (15%)
  4. Experience keyword density (20%)
  5. Education/certification match (5%)
  6. Formatting compliance (10%)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

HARD_SKILL_PATTERNS: List[str] = [
    "sql", "python", "r ", "java", "scala", "javascript",
    "tableau", "power bi", "looker", "excel",
    "snowflake", "redshift", "bigquery", "databricks",
    "dbt", "airflow", "spark", "kafka", "etl", "elt",
    "aws", "azure", "gcp", "cloud",
    "docker", "kubernetes", "terraform", "ci/cd",
    "machine learning", "deep learning", "nlp", "ai",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "data modeling", "data warehouse", "data lake", "data pipeline",
    "data governance", "data quality", "data catalog",
    "agile", "scrum", "jira", "confluence",
    "api", "rest", "graphql", "microservices",
    "git", "github",
    "a/b testing", "statistical analysis", "regression",
    "kpi", "okr", "dashboard",
]

SOFT_SKILL_PATTERNS: List[str] = [
    "leadership", "cross-functional", "stakeholder",
    "communication", "collaboration", "mentoring",
    "problem solving", "analytical", "strategic",
    "project management", "program management",
    "roadmap", "planning", "prioritization",
    "presentation", "executive", "influence",
]


@dataclass
class ATSScoreResult:
    overall_score: int
    hard_skill_score: int
    soft_skill_score: int
    title_score: int
    experience_score: int
    education_score: int
    format_score: int
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ATSScorerService:
    ATS_TARGET = 80

    def score(self, resume_text: str, job_title: str, job_description: str) -> ATSScoreResult:
        resume_lower = resume_text.lower()
        jd_lower = job_description.lower()
        title_lower = job_title.lower()

        jd_hard_skills = [s for s in HARD_SKILL_PATTERNS if s in jd_lower]
        jd_soft_skills = [s for s in SOFT_SKILL_PATTERNS if s in jd_lower]

        if not jd_hard_skills:
            jd_hard_skills = ["sql", "python", "analytics"]

        matched_hard = [s for s in jd_hard_skills if s in resume_lower]
        missing_hard = [s for s in jd_hard_skills if s not in resume_lower]
        hard_pct = (len(matched_hard) / len(jd_hard_skills)) * 100 if jd_hard_skills else 100

        matched_soft = [s for s in jd_soft_skills if s in resume_lower]
        soft_pct = (len(matched_soft) / len(jd_soft_skills)) * 100 if jd_soft_skills else 80

        title_words = set(re.findall(r"\w+", title_lower)) - {"the", "a", "an", "and", "or", "of", "for", "in", "at"}
        title_hits = sum(1 for w in title_words if w in resume_lower)
        title_pct = (title_hits / len(title_words)) * 100 if title_words else 100

        jd_terms = set(re.findall(r"\b\w{4,}\b", jd_lower))
        jd_terms -= {"that", "this", "with", "will", "from", "have", "been", "they", "your", "about", "their", "what"}
        resume_terms = set(re.findall(r"\b\w{4,}\b", resume_lower))
        overlap = jd_terms & resume_terms
        experience_pct = min((len(overlap) / max(len(jd_terms), 1)) * 130, 100)

        edu_terms = ["bachelor", "master", "mba", "phd", "degree", "certified", "certification", "certificate"]
        jd_edu = [e for e in edu_terms if e in jd_lower]
        if jd_edu:
            edu_hits = sum(1 for e in jd_edu if e in resume_lower)
            edu_pct = (edu_hits / len(jd_edu)) * 100
        else:
            edu_pct = 100

        format_pct = 100

        hard_score = round(hard_pct * 0.40)
        soft_score = round(soft_pct * 0.10)
        title_score = round(title_pct * 0.15)
        exp_score = round(experience_pct * 0.20)
        edu_score = round(edu_pct * 0.05)
        fmt_score = round(format_pct * 0.10)
        overall = min(hard_score + soft_score + title_score + exp_score + edu_score + fmt_score, 100)

        suggestions: List[str] = []
        if missing_hard:
            top_missing = missing_hard[:5]
            suggestions.append(f"Add missing keywords: {', '.join(top_missing)}")
        if hard_pct < 70:
            suggestions.append("Hard skill keyword coverage is low — mirror more JD terms in your skills/bullets")
        if title_pct < 60:
            suggestions.append("Job title terms not prominent — add them to your summary or title line")
        if overall < self.ATS_TARGET:
            suggestions.append(f"ATS score {overall}% is below {self.ATS_TARGET}% target — needs more keyword alignment")

        return ATSScoreResult(
            overall_score=overall,
            hard_skill_score=hard_score,
            soft_skill_score=soft_score,
            title_score=title_score,
            experience_score=exp_score,
            education_score=edu_score,
            format_score=fmt_score,
            matched_keywords=matched_hard + matched_soft,
            missing_keywords=missing_hard,
            suggestions=suggestions,
        )
