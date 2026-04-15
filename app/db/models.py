from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default="running")
    jobs_found = Column(Integer, default=0)
    jobs_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    records = relationship("TrackerRecord", back_populates="run")


class TrackerRecord(Base):
    __tablename__ = "tracker_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=False)
    job_id = Column(String(255), nullable=False)
    company = Column(String(255), default="")
    role = Column(String(255), default="")
    fit_score = Column(Float, default=0.0)
    status = Column(String(20), default="success")
    output_path = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    run = relationship("WorkflowRun", back_populates="records")
