from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, List

import requests

from app.schemas.job import JobListing
from app.services.fetchers.base import BaseJobFetcher
from app.services.fetchers.normalizer import normalize_job

logger = logging.getLogger(__name__)

LEVER_API = "https://api.lever.co/v0/postings/{slug}"
DEFAULT_TIMEOUT = 30
MAX_WORKERS = 4


class LeverFetcher(BaseJobFetcher):
    def __init__(self, company_slugs: List[str]) -> None:
        self.company_slugs = company_slugs

    def fetch(self, lookback_hours: int = 24) -> List[JobListing]:
        """Fetch jobs from all Lever companies in parallel."""
        results: List[JobListing] = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(self._fetch_company, slug): slug
                for slug in self.company_slugs
            }
            for future in as_completed(futures):
                slug = futures[future]
                try:
                    jobs = future.result()
                    results.extend(jobs)
                except Exception as exc:
                    logger.warning("Lever [%s] fetch failed: %s", slug, exc)

        logger.info("LeverFetcher total: %d jobs from %d companies", len(results), len(self.company_slugs))
        return results

    def _fetch_company(self, slug: str) -> List[JobListing]:
        url = LEVER_API.format(slug=slug)
        resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        postings = resp.json()
        if not isinstance(postings, list):
            postings = []

        jobs: List[JobListing] = []
        for raw in postings:
            categories = raw.get("categories", {})
            created_ms = raw.get("createdAt", 0)
            posted_str = ""
            if created_ms:
                posted_str = datetime.utcfromtimestamp(created_ms / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")
            normalized = normalize_job(
                {
                    "id": raw.get("id", ""),
                    "title": raw.get("text", ""),
                    "company": slug.replace("-", " ").title(),
                    "location": categories.get("location", ""),
                    "posted_at": posted_str,
                    "url": raw.get("hostedUrl", raw.get("applyUrl", "")),
                    "description": raw.get("descriptionPlain", ""),
                    "source": "lever",
                }
            )
            if normalized:
                jobs.append(normalized)

        logger.info("Lever [%s]: %d postings", slug, len(jobs))
        return jobs
