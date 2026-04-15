from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Callable, List, Optional, Set

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.models import TrackerRecord, WorkflowRun
from app.schemas.tracker import TrackerCreate

logger = logging.getLogger(__name__)


class TrackerService:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory

    def start_run(self) -> WorkflowRun:
        with self.session_factory() as db:
            run = WorkflowRun()
            db.add(run)
            db.commit()
            db.refresh(run)
            logger.info("Started workflow run id=%d", run.id)
            return run

    def finish_run(self, run: WorkflowRun, *, status: str = "completed", jobs_found: int = 0, jobs_processed: int = 0, error: Optional[str] = None) -> None:
        with self.session_factory() as db:
            db_run = db.query(WorkflowRun).get(run.id)
            if db_run:
                db_run.status = status
                db_run.jobs_found = jobs_found
                db_run.jobs_processed = jobs_processed
                db_run.error_message = error
                db.commit()

    def add_records(self, run_id: int, records: List[TrackerCreate]) -> None:
        with self.session_factory() as db:
            for rec in records:
                db_rec = TrackerRecord(
                    run_id=run_id,
                    job_id=rec.job_id,
                    company=rec.company,
                    role=rec.role,
                    fit_score=rec.fit_score,
                    status=rec.status,
                    output_path=rec.output_path,
                )
                db.add(db_rec)
            db.commit()
            logger.info("Saved %d tracking records for run %d", len(records), run_id)

    def get_history(self, limit: int = 10) -> List[WorkflowRun]:
        with self.session_factory() as db:
            return db.query(WorkflowRun).order_by(desc(WorkflowRun.id)).limit(limit).all()

    def get_today_job_ids(self) -> Set[str]:
        today = date.today()
        with self.session_factory() as db:
            rows = (
                db.query(TrackerRecord.job_id)
                .join(WorkflowRun, TrackerRecord.run_id == WorkflowRun.id)
                .filter(func.date(WorkflowRun.run_date) == today)
                .filter(TrackerRecord.status == "success")
                .all()
            )
            return {r[0] for r in rows}
