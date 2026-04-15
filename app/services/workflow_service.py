from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.schemas.job import JobListing
from app.schemas.tracker import TrackerCreate
from app.services.docx_writer import DocxWriterService
from app.services.email_service import EmailService
from app.services.excel_tracker import ExcelTrackerService
from app.services.fetchers.base import BaseJobFetcher
from app.services.job_ranker import JobRankerService
from app.services.llm_service import LLMService
from app.services.output_writer import OutputWriterService
from app.services.profile_search import is_h1b_sponsor
from app.services.resume_loader import ResumeLoaderService
from app.services.resume_tailor import ResumeTailorService
from app.services.tracker_service import TrackerService

logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(
        self,
        *,
        job_fetcher: BaseJobFetcher,
        job_ranker: JobRankerService,
        resume_loader: ResumeLoaderService,
        llm_service: LLMService,
        resume_tailor: ResumeTailorService,
        output_writer: OutputWriterService,
        docx_writer: DocxWriterService,
        tracker_service: TrackerService,
        email_service: EmailService,
        excel_tracker: ExcelTrackerService,
    ) -> None:
        self.job_fetcher = job_fetcher
        self.job_ranker = job_ranker
        self.resume_loader = resume_loader
        self.llm_service = llm_service
        self.resume_tailor = resume_tailor
        self.output_writer = output_writer
        self.docx_writer = docx_writer
        self.tracker_service = tracker_service
        self.email_service = email_service
        self.excel_tracker = excel_tracker

    def run_daily_workflow(self) -> Dict[str, Any]:
        logger.info("=== Workflow run started ===")
        run = self.tracker_service.start_run()
        tracker_rows: List[TrackerCreate] = []
        email_rows: List[Dict[str, Any]] = []
        processed_jobs = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0

        try:
            raw_jobs = self.job_fetcher.fetch(lookback_hours=24)
            logger.info("Jobs fetched: %d", len(raw_jobs))

            ranked_jobs = self.job_ranker.rank(raw_jobs)
            logger.info("Jobs selected after ranking: %d", len(ranked_jobs))

            already_processed = self.tracker_service.get_today_job_ids()
            master_resume = self.resume_loader.load()
            logger.info("Master resume loaded (%d chars)", len(master_resume))

            for job in ranked_jobs:
                if job.id in already_processed:
                    logger.info("Skipping already-processed job: %s at %s", job.title, job.company)
                    skipped_count += 1
                    continue

                processed_jobs += 1
                output_path = Path("")
                docx_path = Path("")
                fit_score = 0.0
                ats_score = 0
                status = "failed"

                try:
                    analysis = self.llm_service.analyze(job, master_resume)
                    tailored_markdown, ats_score = self.resume_tailor.tailor(
                        master_resume,
                        analysis,
                        job_title=job.title,
                        job_description=job.description,
                    )
                    fit_score = analysis.fit_score
                    logger.info(
                        "Tailoring completed: id=%s fit_score=%s ats_score=%d%% reason=%s",
                        job.id, analysis.fit_score, ats_score, analysis.one_line_reason,
                    )

                    output_path = self.output_writer.write_resume(
                        company=job.company, role=job.title, markdown=tailored_markdown,
                    )
                    docx_path = self.docx_writer.write(
                        company=job.company, role=job.title, markdown=tailored_markdown,
                    )
                    logger.info("Files generated: md=%s docx=%s", output_path, docx_path)
                    success_count += 1
                    status = "success"
                except Exception as exc:
                    failed_count += 1
                    logger.error("Tailoring failed for %s at %s: %s", job.title, job.company, exc)

                tracker_rows.append(
                    TrackerCreate(
                        job_id=job.id,
                        company=job.company,
                        role=job.title,
                        fit_score=fit_score,
                        status=status,
                        output_path=str(output_path),
                    )
                )

                h1b = "Yes" if is_h1b_sponsor(job.company) else ""
                email_rows.append(
                    {
                        "company": job.company,
                        "role": job.title,
                        "location": job.location,
                        "remote_type": job.remote_type,
                        "posted": job.posted_at.strftime("%Y-%m-%d"),
                        "relevance": f"{job.relevance_score:.0f}%",
                        "fit_score": fit_score,
                        "ats_score": f"{ats_score}%",
                        "h1b_sponsor": h1b,
                        "reason": analysis.one_line_reason if status == "success" else "Processing failed",
                        "output_path": str(docx_path) if docx_path.name else str(output_path),
                        "apply_url": job.url,
                        "status": status,
                    }
                )

            if tracker_rows:
                self.tracker_service.add_records(run.id, tracker_rows)

            if email_rows:
                self.email_service.send_summary(email_rows, run.id)
                self.excel_tracker.append_rows(email_rows)
                logger.info("Email and Excel tracker generated")

            self.tracker_service.finish_run(
                run, status="completed", jobs_found=len(raw_jobs), jobs_processed=processed_jobs,
            )
            logger.info(
                "=== Workflow completed: run_id=%s processed=%s success=%s failed=%s skipped=%s ===",
                run.id, processed_jobs, success_count, failed_count, skipped_count,
            )

        except Exception as exc:
            logger.exception("Workflow failed: %s", exc)
            self.tracker_service.finish_run(run, status="failed", error=str(exc))

        return {
            "run_id": run.id,
            "jobs_found": len(raw_jobs) if "raw_jobs" in dir() else 0,
            "jobs_processed": processed_jobs,
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
        }
