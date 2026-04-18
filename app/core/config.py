from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class SearchProfile(BaseModel):
    target_roles: List[str] = Field(
        default_factory=lambda: [
            "Technical Program Manager",
            "Program Manager",
            "Senior Program Manager",
            "Data Program Manager",
            "Analytics Manager",
            "Data Analyst",
            "Senior Data Analyst",
            "Business Data Analyst",
            "Analytics Engineer",
            "Data Engineer",
            "TPM",
        ]
    )
    priority_keywords: List[str] = Field(
        default_factory=lambda: [
            "sql", "python", "snowflake", "dbt", "aws", "etl", "data platform",
            "data governance", "agile", "scrum", "roadmap", "cross-functional",
            "tableau", "power bi", "data modeling", "analytics", "stakeholder",
            "program management", "financial services", "banking", "finance",
            "regulatory", "risk", "compliance", "remote",
        ]
    )
    remote_preferred: bool = True
    max_daily_jobs: int = 30
    min_relevance_score: float = 50.0


class Settings(BaseSettings):
    app_name: str = "AI Resume Tailoring Workflow"
    debug: bool = False

    llm_provider: str = "mock"
    openai_api_key: str = ""
    gemini_api_key: str = ""

    job_source_provider: str = "startups"
    apify_api_token: str = ""
    apify_actor_id: str = ""
    apify_run_mode: str = "last_run"
    apify_search_queries: List[str] = Field(default_factory=list)
    apify_search_location: str = "United States"
    greenhouse_company_slugs: List[str] = Field(default_factory=list)
    lever_company_slugs: List[str] = Field(default_factory=list)

    resume_source: str = "local"
    gdrive_file_id: str = ""
    gdrive_api_key: str = ""

    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = ""

    schedule_timezone: str = "America/New_York"

    db_url: str = f"sqlite:///{BASE_DIR / 'data' / 'workflow.db'}"
    output_dir: Path = BASE_DIR / "data" / "output"
    resume_dir: Path = BASE_DIR / "data" / "resumes"
    mock_data_path: Path = BASE_DIR / "mock_data" / "mock_jobs.json"
    template_dir: Path = BASE_DIR / "app" / "templates"
    tracker_xlsx_path: Path = BASE_DIR / "data" / "output" / "job_tracker.xlsx"

    search_profile: SearchProfile = Field(default_factory=SearchProfile)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
