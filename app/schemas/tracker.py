from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TrackerCreate(BaseModel):
    job_id: str
    company: str
    role: str
    fit_score: float = 0.0
    status: str = "success"
    output_path: str = ""


class TrackerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    job_id: str
    company: str
    role: str
    fit_score: float
    status: str
    output_path: str
    created_at: datetime
