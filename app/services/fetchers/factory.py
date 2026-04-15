from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from app.services.fetchers.base import BaseJobFetcher

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


class MultiFetcher(BaseJobFetcher):
    def __init__(self, fetchers: List[BaseJobFetcher]) -> None:
        self.fetchers = fetchers

    def fetch(self, lookback_hours: int = 24):
        from app.schemas.job import JobListing

        all_jobs: List[JobListing] = []
        for fetcher in self.fetchers:
            try:
                jobs = fetcher.fetch(lookback_hours)
                all_jobs.extend(jobs)
                logger.info("%s returned %d jobs", type(fetcher).__name__, len(jobs))
            except Exception as exc:
                logger.warning("%s failed: %s", type(fetcher).__name__, exc)
        logger.info("MultiFetcher total: %d jobs from %d sources", len(all_jobs), len(self.fetchers))
        return all_jobs


def create_fetcher(settings: "Settings") -> BaseJobFetcher:
    provider = settings.job_source_provider.lower().strip()

    if provider == "all":
        fetchers = _build_all_fetchers(settings)
        return MultiFetcher(fetchers) if fetchers else _build_single("mock", settings)

    if provider == "startups":
        fetchers = _build_startup_fetchers(settings)
        return MultiFetcher(fetchers) if fetchers else _build_single("mock", settings)

    if "," in provider:
        fetchers = []
        for p in provider.split(","):
            f = _build_single(p.strip(), settings)
            if f:
                fetchers.append(f)
        return MultiFetcher(fetchers) if fetchers else _build_single("mock", settings)

    return _build_single(provider, settings) or _build_single("mock", settings)


def _build_all_fetchers(settings: "Settings") -> List[BaseJobFetcher]:
    fetchers: List[BaseJobFetcher] = []
    apify = _build_single("apify", settings)
    if apify:
        fetchers.append(apify)
    fetchers.extend(_build_startup_fetchers(settings))
    return fetchers


def _build_startup_fetchers(settings: "Settings") -> List[BaseJobFetcher]:
    from app.services.profile_search import get_startup_greenhouse_slugs, get_startup_lever_slugs
    from app.services.fetchers.greenhouse_fetcher import GreenhouseFetcher
    from app.services.fetchers.lever_fetcher import LeverFetcher

    fetchers: List[BaseJobFetcher] = []
    gh_slugs = settings.greenhouse_company_slugs or get_startup_greenhouse_slugs()
    lv_slugs = settings.lever_company_slugs or get_startup_lever_slugs()
    if gh_slugs:
        fetchers.append(GreenhouseFetcher(gh_slugs))
    if lv_slugs:
        fetchers.append(LeverFetcher(lv_slugs))
    return fetchers


def _build_single(provider: str, settings: "Settings") -> Optional[BaseJobFetcher]:
    if provider == "mock":
        from app.services.fetchers.mock_fetcher import MockJobFetcher
        return MockJobFetcher(settings.mock_data_path)

    if provider == "greenhouse":
        from app.services.fetchers.greenhouse_fetcher import GreenhouseFetcher
        from app.services.profile_search import get_startup_greenhouse_slugs
        slugs = settings.greenhouse_company_slugs or get_startup_greenhouse_slugs()
        return GreenhouseFetcher(slugs)

    if provider == "lever":
        from app.services.fetchers.lever_fetcher import LeverFetcher
        from app.services.profile_search import get_startup_lever_slugs
        slugs = settings.lever_company_slugs or get_startup_lever_slugs()
        return LeverFetcher(slugs)

    if provider == "apify":
        from app.services.fetchers.apify_fetcher import ApifyFetcher
        search_queries = list(settings.apify_search_queries)
        if not search_queries:
            from app.services.profile_search import generate_search_queries
            search_queries = generate_search_queries(settings.search_profile)
        return ApifyFetcher(
            api_token=settings.apify_api_token,
            actor_id=settings.apify_actor_id,
            run_mode=settings.apify_run_mode,
            search_queries=search_queries,
            search_location=settings.apify_search_location,
        )

    logger.warning("Unknown job source provider: %s — falling back to mock", provider)
    return None
