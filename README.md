# AI Resume Tailoring Workflow

Automated daily job discovery, resume tailoring, ATS scoring, and email summary system.

## Features

- **Job Discovery**: Fetch jobs from mock data, Apify (LinkedIn/Indeed), Greenhouse, Lever
- **Smart Ranking**: Score jobs 0-100% based on role match, keywords, freshness, remote preference, domain relevance, H1B sponsorship
- **Resume Tailoring**: LLM-powered resume customization per job description
- **ATS Scoring**: 0-100% ATS compatibility score with auto-boost to 80%+ target
- **Word Documents**: Professional `.docx` output ready to submit
- **Excel Tracker**: `job_tracker.xlsx` with all jobs, scores, and apply links
- **Email Summary**: HTML email preview with color-coded ATS scores and H1B badges
- **Scheduling**: Runs at 7 AM, 12 PM, 5 PM daily with cross-run deduplication

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with mock data (no API keys needed)
python scripts/run_workflow.py

# Or start the API server
uvicorn app.main:app --reload
```

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | mock / openai / gemini | mock |
| `JOB_SOURCE_PROVIDER` | mock / apify / greenhouse / lever / all | mock |
| `RESUME_SOURCE` | local / gdrive | local |
| `EMAIL_ENABLED` | true / false | false |

## API Endpoints

- `GET /health` — Health check
- `POST /workflow/run` — Trigger workflow manually
- `GET /workflow/history` — View past runs

## Project Structure

```
app/
├── api/routes.py          # FastAPI endpoints
├── core/                  # Config, logging, scheduler
├── db/                    # SQLAlchemy models & session
├── schemas/               # Pydantic models
├── services/
│   ├── fetchers/          # Job source integrations
│   ├── ats_scorer.py      # ATS compatibility scoring
│   ├── job_ranker.py      # Job relevance ranking
│   ├── llm_service.py     # LLM integration
│   ├── resume_tailor.py   # Resume customization
│   ├── docx_writer.py     # Word document generation
│   ├── excel_tracker.py   # Excel job tracker
│   └── workflow_service.py # Main orchestrator
├── templates/             # Email HTML templates
└── main.py               # App entry point
data/
├── resumes/               # Master resume(s)
└── output/                # Generated files
```

## Docker Deployment

```bash
docker-compose up --build -d
```

## Testing

```bash
python -m pytest -v
```
