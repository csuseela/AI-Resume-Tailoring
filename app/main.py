from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI

from app.api.routes import router, set_container
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.scheduler import start_scheduler
from app.db.session import SessionLocal
from app.services.docx_writer import DocxWriterService
from app.services.email_service import EmailService
from app.services.excel_tracker import ExcelTrackerService
from app.services.fetchers.factory import create_fetcher
from app.services.job_ranker import JobRankerService
from app.services.llm_service import LLMService
from app.services.output_writer import OutputWriterService
from app.services.resume_loader import ResumeLoaderService
from app.services.resume_tailor import ResumeTailorService
from app.services.tracker_service import TrackerService
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)


def build_container() -> Dict[str, Any]:
    settings = get_settings()

    job_fetcher = create_fetcher(settings)
    job_ranker = JobRankerService(settings.search_profile)
    resume_loader = ResumeLoaderService(
        resume_dir=settings.resume_dir,
        source=settings.resume_source,
        gdrive_file_id=settings.gdrive_file_id,
        gdrive_api_key=settings.gdrive_api_key,
    )
    llm_service = LLMService(provider=settings.llm_provider, api_key=settings.openai_api_key)
    resume_tailor = ResumeTailorService()
    output_writer = OutputWriterService(settings.output_dir)
    docx_writer = DocxWriterService(settings.output_dir)
    tracker_service = TrackerService(SessionLocal)
    email_service = EmailService(
        template_dir=settings.template_dir,
        output_dir=settings.output_dir,
        enabled=settings.email_enabled,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        email_to=settings.email_to,
    )
    excel_tracker = ExcelTrackerService(settings.tracker_xlsx_path)

    workflow_service = WorkflowService(
        job_fetcher=job_fetcher,
        job_ranker=job_ranker,
        resume_loader=resume_loader,
        llm_service=llm_service,
        resume_tailor=resume_tailor,
        output_writer=output_writer,
        docx_writer=docx_writer,
        tracker_service=tracker_service,
        email_service=email_service,
        excel_tracker=excel_tracker,
    )

    return {
        "workflow_service": workflow_service,
        "tracker_service": tracker_service,
        "settings": settings,
    }


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="AI Resume Tailoring Workflow")
    container = build_container()
    set_container(container)
    app.include_router(router)

    settings = container["settings"]
    start_scheduler(container["workflow_service"], settings.schedule_timezone)
    logger.info("Application started — %s", settings.app_name)

    return app


app = create_app()
