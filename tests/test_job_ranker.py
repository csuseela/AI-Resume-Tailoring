from datetime import datetime, timedelta, timezone

from app.core.config import SearchProfile
from app.schemas.job import JobListing
from app.services.job_ranker import JobRankerService


def _job(
    job_id: str = "j1",
    title: str = "Data Analyst",
    company: str = "TestCo",
    location: str = "Remote",
    url: str = "https://example.com",
    description: str = "",
    hours_ago: int = 2,
) -> JobListing:
    return JobListing(
        id=job_id,
        title=title,
        company=company,
        location=location,
        posted_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        url=url,
        description=description,
        source="mock",
        remote_type="remote" if "remote" in location.lower() else "onsite",
    )


def test_job_ranker_returns_relevant_jobs_sorted_by_score() -> None:
    profile = SearchProfile(max_daily_jobs=5, min_relevance_score=10.0)
    ranker = JobRankerService(profile)
    jobs = [
        _job(
            job_id=f"job-{idx}",
            title="Data Analyst" if idx % 2 == 0 else "Program Manager",
            company=f"Company {idx}",
            location="Remote" if idx % 2 == 0 else "New York",
            url=f"https://example.com/{idx}",
            description="SQL Python ETL analytics stakeholder program management agile",
            hours_ago=idx + 1,
        )
        for idx in range(8)
    ]

    ranked = ranker.rank(jobs)
    assert len(ranked) <= 5
    assert len(ranked) >= 1
    assert ranked[0].relevance_score >= ranked[-1].relevance_score
    assert all(j.relevance_score <= 100 for j in ranked)


def test_job_ranker_deduplicates_same_company_title_url() -> None:
    profile = SearchProfile(max_daily_jobs=10, min_relevance_score=1.0)
    ranker = JobRankerService(profile)
    jobs = [
        _job(job_id="dup-1", title="Data Analyst", company="ACME", url="https://acme.com/1", description="sql python analytics"),
        _job(job_id="dup-2", title="Data Analyst", company="ACME", url="https://acme.com/1", description="sql python analytics"),
        _job(job_id="dup-3", title="Data Analyst", company="ACME", url="https://acme.com/2", description="sql python analytics"),
    ]
    ranked = ranker.rank(jobs)
    assert len(ranked) == 2
