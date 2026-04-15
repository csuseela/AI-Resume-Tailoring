from __future__ import annotations

import logging
from typing import Any, List

import requests

from app.schemas.job import JobListing
from app.services.fetchers.base import BaseJobFetcher
from app.services.fetchers.normalizer import normalize_job

logger = logging.getLogger(__name__)

LEVER_API = "https://api.lever.co/v0/postings/{slug}"
DEFAULT_TIMEOUT = 30


class LeverFetcher(BaseJobFetcher):
    def __init__(self, company_slugs: List[str]) -> None:
        self.company_slugs = company_slugs

    def fetch(self, lookback_hours: int = 24) -> List[JobListing]:
        jobs: List[JobListing] = []
        for slug in self.company_slugs:
            try:
                url = LEVER_API.format(slug=slug)
                resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
                resp.raise_for_status()
                postings = resp.json()
                if not isinstance(postings, list):
                    postings = []
                for raw in postings:
                    categories = raw.get("categories", {})
                    normalized = normalize_job(
                        {
                            "id": raw.get("id", ""),
                            "title": raw.get("text", ""),
                            "company": slug.replace("-", " ").title(),
                            "location": categories.get("location", ""),
                            "posted_at": "",
                            "url": raw.get("hostedUrl", raw.get("applyUrl", "")),
                            "description": raw.get("descriptionPlain", ""),
                            "source": "lever",
                        }
                    )
                    if normalized:
                        jobs.append(normalized)
                logger.info("Lever [%s]: fetched %d postings", slug, len(postings))
            except Exception as exc:
                logger.warning("Lever [%s] fetch failed: %s", slug, exc)
        return jobs
