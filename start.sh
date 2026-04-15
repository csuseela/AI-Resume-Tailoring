#!/bin/bash
# Production startup script for AI Resume Tailoring
# Runs the FastAPI server with auto-reload disabled for stability

cd "$(dirname "$0")"

echo "================================================"
echo "  AI Resume Tailoring — Production Server"
echo "================================================"
echo ""
echo "  Dashboard:  http://localhost:8000"
echo "  Health:     http://localhost:8000/health"
echo "  Scheduler:  7:00 AM daily (America/New_York)"
echo ""
echo "================================================"
echo ""

exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
