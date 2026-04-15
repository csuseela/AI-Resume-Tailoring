from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Set

from app.core.config import SearchProfile
from app.schemas.job import JobListing
from app.services.profile_search import is_h1b_sponsor

logger = logging.getLogger(__name__)

SENIORITY_NEGATIVE = [
    "vp ", "vice president", "chief", "c-suite", "cto", "cdo", "cio",
]

JUNIOR_NEGATIVE = [
    "intern", "internship", "entry level", "entry-level", "junior", "associate analyst",
]

DOMAIN_TERMS = [
    "financial", "banking", "fintech", "finance", "insurance",
    "analytics", "data", "reporting", "dashboard", "bi ",
    "etl", "pipeline", "warehouse", "modeling",
    "regulatory", "compliance", "risk", "audit",
]


class JobRankerService:
    def __init__(self, profile: SearchProfile) -> None:
        self.profile = profile

    def rank(self, jobs: List[JobListing]) -> List[JobListing]:
        unique = self._dedupe(jobs)
        min_score = self.profile.min_relevance_score
        ranked: List[JobListing] = []
        for job in unique:
            score = self._score(job)
            if score >= min_score:
                ranked.append(job.model_copy(update={"relevance_score": score}))
        ranked.sort(key=lambda j: j.relevance_score, reverse=True)

        top = ranked[:self.profile.max_daily_jobs] if self.profile.max_daily_jobs > 0 else ranked

        for job in top:
            h1b_tag = " [H1B sponsor]" if is_h1b_sponsor(job.company) else ""
            logger.info(
                "Ranked job: %s at %s — score=%d%% (remote=%s)%s",
                job.title, job.company, job.relevance_score, job.remote_type, h1b_tag,
            )
        return top

    def _score(self, job: JobListing) -> float:
        title_lower = job.title.lower()
        desc_lower = job.description.lower()
        text = f"{title_lower} {desc_lower}"

        # Role title match (0-25)
        role_raw = 0.0
        for role in self.profile.target_roles:
            if role.lower() in title_lower:
                role_raw = 25.0
                break
            if any(w in title_lower for w in role.lower().split()):
                role_raw = max(role_raw, 12.0)

        # Keyword match (0-30)
        kw_hits = sum(1 for kw in self.profile.priority_keywords if kw.lower() in text)
        kw_total = len(self.profile.priority_keywords) or 1
        keyword_raw = min((kw_hits / kw_total) * 40, 30.0)

        # Freshness (0-10)
        hours_old = (datetime.now(timezone.utc) - job.posted_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if hours_old <= 12:
            freshness_raw = 10.0
        elif hours_old <= 24:
            freshness_raw = 8.0
        elif hours_old <= 48:
            freshness_raw = 5.0
        elif hours_old <= 72:
            freshness_raw = 3.0
        else:
            freshness_raw = 1.0

        # Remote preference (0-5)
        remote_raw = 0.0
        if self.profile.remote_preferred and job.remote_type == "remote":
            remote_raw = 5.0
        elif job.remote_type == "hybrid":
            remote_raw = 2.5

        # Domain relevance (0-15)
        domain_hits = sum(1 for t in DOMAIN_TERMS if t in text)
        domain_raw = min(domain_hits * 2.5, 15.0)

        # H1B sponsor (0-10)
        h1b_raw = 0.0
        if is_h1b_sponsor(job.company):
            h1b_raw = 7.0
        elif "h1b" in text or "sponsor" in text or "visa" in text:
            h1b_raw = 3.0

        # Seniority penalty
        seniority_penalty = 0.0
        if any(neg in title_lower for neg in SENIORITY_NEGATIVE):
            seniority_penalty = -15.0
        if any(neg in title_lower for neg in JUNIOR_NEGATIVE):
            seniority_penalty = -10.0

        raw = role_raw + keyword_raw + freshness_raw + remote_raw + domain_raw + h1b_raw + seniority_penalty
        return round(max(min(raw, 100.0), 0.0))

    @staticmethod
    def _dedupe(jobs: List[JobListing]) -> List[JobListing]:
        seen: Set[str] = set()
        unique: List[JobListing] = []
        for job in jobs:
            key = f"{job.company.lower()}:{job.title.lower()}:{job.url}"
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique
