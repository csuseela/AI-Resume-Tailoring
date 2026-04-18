from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

import requests

from app.schemas.job import JobListing
from app.services.fetchers.base import BaseJobFetcher
from app.services.fetchers.normalizer import normalize_job

logger = logging.getLogger(__name__)

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
GREENHOUSE_JOB_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"
DEFAULT_TIMEOUT = 30
MAX_WORKERS = 8


class GreenhouseFetcher(BaseJobFetcher):
    def __init__(self, company_slugs: List[str]) -> None:
        self.company_slugs = company_slugs

    def fetch(self, lookback_hours: int = 24) -> List[JobListing]:
        """Fetch jobs from all companies in parallel, without full descriptions."""
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
                    logger.warning("Greenhouse [%s] fetch failed: %s", slug, exc)

        logger.info("GreenhouseFetcher total: %d jobs from %d companies", len(results), len(self.company_slugs))
        return results

    def _fetch_company(self, slug: str) -> List[JobListing]:
        """Fetch job listings for one company (metadata only, no full HTML content)."""
        url = GREENHOUSE_API.format(slug=slug)
        resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        jobs: List[JobListing] = []
        for raw_job in data.get("jobs", []):
            job_id = str(raw_job.get("id", ""))
            board_url = f"https://job-boards.greenhouse.io/{slug}/jobs/{job_id}"

            metadata = raw_job.get("metadata", [])
            departments = raw_job.get("departments", [])
            dept_names = " ".join(d.get("name", "") for d in departments)

            normalized = normalize_job(
                {
                    "id": job_id,
                    "title": raw_job.get("title", ""),
                    "company": slug.replace("-", " ").title(),
                    "location": raw_job.get("location", {}).get("name", ""),
                    "posted_at": raw_job.get("updated_at", ""),
                    "url": board_url,
                    "description": dept_names,
                    "source": "greenhouse",
                }
            )
            if normalized:
                jobs.append(normalized)

        logger.info("Greenhouse [%s]: %d postings", slug, len(jobs))
        return jobs

    @staticmethod
    def fetch_job_description(slug: str, job_id: str) -> str:
        """Fetch full description for a single job (called only for ranked jobs)."""
        try:
            url = GREENHOUSE_JOB_API.format(slug=slug, job_id=job_id)
            resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp.json().get("content", "")
        except Exception as exc:
            logger.warning("Failed to fetch description for %s/%s: %s", slug, job_id, exc)
            return ""
