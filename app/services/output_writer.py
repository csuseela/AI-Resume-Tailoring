from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class OutputWriterService:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_resume(self, company: str, role: str, markdown: str) -> Path:
        slug_company = re.sub(r"[^a-zA-Z0-9]+", "_", company.strip().lower()).strip("_")
        slug_role = re.sub(r"[^a-zA-Z0-9]+", "_", role.strip().lower()).strip("_")
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{slug_company}_{slug_role}.md"
        path = self.output_dir / filename
        path.write_text(markdown, encoding="utf-8")
        logger.info("Resume written: %s", path)
        return path
