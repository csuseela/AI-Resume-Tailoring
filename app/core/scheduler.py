from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

SCHEDULE_HOURS = [7]


def start_scheduler(workflow_service: WorkflowService, timezone: str) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=timezone)

    def _run_workflow() -> None:
        logger.info("Scheduled workflow trigger fired")
        workflow_service.run_daily_workflow()

    for hour in SCHEDULE_HOURS:
        job_id = f"workflow_run_{hour:02d}00"
        scheduler.add_job(
            _run_workflow,
            trigger=CronTrigger(hour=hour, minute=0, timezone=timezone),
            id=job_id,
            replace_existing=True,
        )

    scheduler.start()
    schedule_str = ", ".join(f"{h}:00" for h in SCHEDULE_HOURS)
    logger.info("Scheduler started — runs at %s (%s)", schedule_str, timezone)
    return scheduler
