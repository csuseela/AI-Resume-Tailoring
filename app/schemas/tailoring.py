from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class TailoringResult(BaseModel):
    summary: Optional[str] = None
    skills: Optional[str] = None
    experience_bullets: Optional[Dict[str, List[str]]] = None
    fit_score: float = 0.0
    one_line_reason: str = ""
