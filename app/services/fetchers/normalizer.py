from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Optional

from app.schemas.job import JobListing

logger = logging.getLogger(__name__)

REMOTE_KEYWORDS = {"remote", "work from home", "wfh", "distributed", "anywhere"}
HYBRID_KEYWORDS = {"hybrid", "flex"}


def normalize_job(raw: dict[str, Any]) -> Optional[JobListing]:
    try:
        title = raw.get("title", "").strip()
        company = raw.get("company", raw.get("company_name", "")).strip()
        if not title or not company:
            return None

        location = raw.get("location", "").strip()
        remote_type = _detect_remote(title, location, raw.get("description", ""))

        posted_str = raw.get("posted_at", raw.get("postedAt", ""))
        posted_at = _parse_date(posted_str) if posted_str else datetime.utcnow()

        job_id = raw.get("id", raw.get("externalId", ""))
        if not job_id:
            job_id = hashlib.md5(f"{company}:{title}:{posted_str}".encode()).hexdigest()[:12]

        return JobListing(
            id=str(job_id),
            title=title,
            company=company,
            location=location,
            posted_at=posted_at,
            url=raw.get("url", raw.get("apply_url", "")),
            description=raw.get("description", ""),
            source=raw.get("source", "unknown"),
            remote_type=remote_type,
            employment_type=raw.get("employment_type", "full-time"),
        )
    except Exception as exc:
        logger.warning("Failed to normalize job: %s", exc)
        return None


def _detect_remote(title: str, location: str, description: str) -> str:
    text = f"{title} {location} {description}".lower()
    if any(kw in text for kw in REMOTE_KEYWORDS):
        return "remote"
    if any(kw in text for kw in HYBRID_KEYWORDS):
        return "hybrid"
    return "onsite"


def _parse_date(date_str: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.utcnow()
