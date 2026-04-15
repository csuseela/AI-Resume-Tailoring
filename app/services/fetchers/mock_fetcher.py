from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List

from app.schemas.job import JobListing
from app.services.fetchers.base import BaseJobFetcher
from app.services.fetchers.normalizer import normalize_job

logger = logging.getLogger(__name__)


class MockJobFetcher(BaseJobFetcher):
    def __init__(self, mock_data_path: Path) -> None:
        self.mock_data_path = mock_data_path

    def fetch(self, lookback_hours: int = 24) -> List[JobListing]:
        logger.info("Fetching jobs from mock data: %s", self.mock_data_path)
        try:
            with open(self.mock_data_path) as f:
                raw_jobs: List[dict] = json.load(f)
        except Exception as exc:
            logger.error("Failed to read mock data: %s", exc)
            return []

        jobs = []
        for raw in raw_jobs:
            raw["source"] = "mock"
            job = normalize_job(raw)
            if job:
                jobs.append(job)

        logger.info("Loaded %d mock jobs", len(jobs))
        return jobs
