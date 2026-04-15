from __future__ import annotations

import logging
import time
from typing import Any, List, Optional

import requests

from app.schemas.job import JobListing
from app.services.fetchers.base import BaseJobFetcher
from app.services.fetchers.normalizer import normalize_job

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60
POLL_INTERVAL = 10
MAX_POLL_SECONDS = 300


class ApifyFetcher(BaseJobFetcher):
    def __init__(
        self,
        api_token: str,
        actor_id: str,
        run_mode: str = "last_run",
        search_queries: Optional[List[str]] = None,
        search_location: str = "United States",
    ) -> None:
        self.api_token = api_token
        self.actor_id = actor_id
        self.run_mode = run_mode
        self.search_queries = search_queries or []
        self.search_location = search_location
        self.base_url = f"https://api.apify.com/v2/acts/{actor_id}"

    def fetch(self, lookback_hours: int = 24) -> List[JobListing]:
        if not self.api_token or not self.actor_id:
            logger.warning("Apify credentials not configured — skipping")
            return []

        try:
            if self.run_mode == "on_demand" and self.search_queries:
                raw_items = self._run_actor_and_poll()
            else:
                raw_items = self._get_last_run_dataset()
        except Exception as exc:
            logger.error("Apify fetch failed: %s", exc)
            return []

        jobs: List[JobListing] = []
        for item in raw_items:
            normalized = normalize_job(
                {
                    "id": item.get("id", item.get("externalId", "")),
                    "title": item.get("title", item.get("positionName", "")),
                    "company": item.get("company", item.get("companyName", "")),
                    "location": item.get("location", ""),
                    "posted_at": item.get("postedAt", item.get("date", "")),
                    "url": item.get("url", item.get("jobUrl", "")),
                    "description": item.get("description", item.get("descriptionText", "")),
                    "source": "apify",
                }
            )
            if normalized:
                jobs.append(normalized)

        logger.info("Apify: fetched %d jobs from %d raw items", len(jobs), len(raw_items))
        return jobs

    def _get_last_run_dataset(self) -> List[dict]:
        url = f"{self.base_url}/runs/last/dataset/items"
        return self._get_with_retries(url)

    def _run_actor_and_poll(self) -> List[dict]:
        run_url = f"{self.base_url}/runs?token={self.api_token}"
        payload = {
            "queries": self.search_queries,
            "location": self.search_location,
            "maxItems": 100,
        }
        resp = requests.post(run_url, json=payload, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        run_data = resp.json().get("data", {})
        run_id = run_data.get("id", "")
        logger.info("Apify actor run started: %s", run_id)

        dataset_id = self._poll_until_done(run_id)
        if not dataset_id:
            return []

        items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={self.api_token}"
        return self._get_with_retries(items_url)

    def _poll_until_done(self, run_id: str) -> Optional[str]:
        url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.api_token}"
        elapsed = 0
        while elapsed < MAX_POLL_SECONDS:
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            try:
                resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
                resp.raise_for_status()
                data = resp.json().get("data", {})
                status = data.get("status", "")
                if status == "SUCCEEDED":
                    return data.get("defaultDatasetId", "")
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    logger.error("Apify run %s ended with status: %s", run_id, status)
                    return None
                logger.debug("Apify run %s status: %s (%ds)", run_id, status, elapsed)
            except Exception as exc:
                logger.warning("Poll error: %s", exc)
        logger.error("Apify run %s timed out after %ds", run_id, MAX_POLL_SECONDS)
        return None

    def _get_with_retries(self, url: str, max_retries: int = 3) -> List[dict]:
        params = {"token": self.api_token} if "token=" not in url else {}
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
                resp.raise_for_status()
                return resp.json() if isinstance(resp.json(), list) else []
            except Exception as exc:
                logger.warning("Apify GET attempt %d failed: %s", attempt + 1, exc)
                time.sleep(attempt * 2)
        return []
