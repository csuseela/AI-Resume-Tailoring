import json
import tempfile
from pathlib import Path

from app.core.config import SearchProfile
from app.services.docx_writer import DocxWriterService
from app.services.email_service import EmailService
from app.services.excel_tracker import ExcelTrackerService
from app.services.fetchers.mock_fetcher import MockJobFetcher
from app.services.job_ranker import JobRankerService
from app.services.llm_service import LLMService
from app.services.output_writer import OutputWriterService
from app.services.resume_loader import ResumeLoaderService
from app.services.resume_tailor import ResumeTailorService
from app.services.tracker_service import TrackerService
from app.services.workflow_service import WorkflowService

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base


def test_workflow_end_to_end() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        output_dir = tmp / "output"
        output_dir.mkdir()
        resume_dir = tmp / "resumes"
        resume_dir.mkdir()
        template_dir = Path(__file__).resolve().parent.parent / "app" / "templates"

        (resume_dir / "resume.md").write_text("# Test Resume\n\n## Summary\nTest.\n\n## Skills\nSQL\n")

        mock_data = tmp / "mock_jobs.json"
        mock_data.write_text(json.dumps([
            {
                "id": "test-1",
                "title": "Data Analyst",
                "company": "TestCo",
                "location": "Remote",
                "posted_at": "2026-04-15T10:00:00Z",
                "url": "https://example.com/1",
                "description": "SQL Python analytics dashboard stakeholder",
                "source": "mock",
                "remote_type": "remote",
            }
        ]))

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)

        wf = WorkflowService(
            job_fetcher=MockJobFetcher(mock_data),
            job_ranker=JobRankerService(SearchProfile(max_daily_jobs=5, min_relevance_score=1.0)),
            resume_loader=ResumeLoaderService(resume_dir),
            llm_service=LLMService(provider="mock"),
            resume_tailor=ResumeTailorService(),
            output_writer=OutputWriterService(output_dir),
            docx_writer=DocxWriterService(output_dir),
            tracker_service=TrackerService(Session),
            email_service=EmailService(template_dir=template_dir, output_dir=output_dir),
            excel_tracker=ExcelTrackerService(output_dir / "tracker.xlsx"),
        )

        result = wf.run_daily_workflow()
        assert result["success_count"] >= 1
        assert result["failed_count"] == 0

        md_files = list(output_dir.glob("*.md"))
        docx_files = list(output_dir.glob("*.docx"))
        assert len(md_files) >= 1
        assert len(docx_files) >= 1
