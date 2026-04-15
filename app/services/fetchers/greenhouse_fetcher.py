from __future__ import annotations

import logging
from typing import Any, List

import requests

from app.schemas.job import JobListing
from app.services.fetchers.base import BaseJobFetcher
from app.services.fetchers.normalizer import normalize_job

logger = logging.getLogger(__name__)

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
DEFAULT_TIMEOUT = 30


class GreenhouseFetcher(BaseJobFetcher):
    def __init__(self, company_slugs: List[str]) -> None:
        self.company_slugs = company_slugs

    def fetch(self, lookback_hours: int = 24) -> List[JobListing]:
        jobs: List[JobListing] = []
        for slug in self.company_slugs:
            try:
                url = GREENHOUSE_API.format(slug=slug)
                resp = requests.get(url, timeout=DEFAULT_TIMEOUT, params={"content": "true"})
                resp.raise_for_status()
                data = resp.json()
                for raw_job in data.get("jobs", []):
                    normalized = normalize_job(
                        {
                            "id": str(raw_job.get("id", "")),
                            "title": raw_job.get("title", ""),
                            "company": slug.replace("-", " ").title(),
                            "location": raw_job.get("location", {}).get("name", ""),
                            "posted_at": raw_job.get("updated_at", ""),
                            "url": raw_job.get("absolute_url", ""),
                            "description": raw_job.get("content", ""),
                            "source": "greenhouse",
                        }
                    )
                    if normalized:
                        jobs.append(normalized)
                logger.info("Greenhouse [%s]: fetched %d postings", slug, len(data.get("jobs", [])))
            except Exception as exc:
                logger.warning("Greenhouse [%s] fetch failed: %s", slug, exc)
        return jobs
