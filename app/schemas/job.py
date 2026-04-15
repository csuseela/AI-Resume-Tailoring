from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobListing(BaseModel):
    id: str
    title: str
    company: str
    location: str = ""
    posted_at: datetime = Field(default_factory=datetime.utcnow)
    url: str = ""
    description: str = ""
    source: str = "mock"
    remote_type: str = "unknown"
    employment_type: str = "full-time"
    relevance_score: float = 0.0
