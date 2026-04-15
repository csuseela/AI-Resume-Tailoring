from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

_container: Dict[str, Any] = {}


def set_container(container: Dict[str, Any]) -> None:
    global _container
    _container = container


@router.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


@router.post("/workflow/run")
def run_workflow() -> Dict[str, Any]:
    wf = _container.get("workflow_service")
    if not wf:
        raise HTTPException(status_code=500, detail="Workflow service not initialized")
    result = wf.run_daily_workflow()
    return result


@router.get("/workflow/history")
def workflow_history() -> Any:
    tracker = _container.get("tracker_service")
    if not tracker:
        raise HTTPException(status_code=500, detail="Tracker not initialized")
    runs = tracker.get_history(limit=20)
    return [
        {
            "id": r.id,
            "run_date": str(r.run_date),
            "status": r.status,
            "jobs_found": r.jobs_found,
            "jobs_processed": r.jobs_processed,
        }
        for r in runs
    ]
