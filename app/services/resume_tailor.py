from __future__ import annotations

import logging
import re
from typing import Tuple

from app.schemas.tailoring import TailoringResult
from app.services.ats_scorer import ATSScorerService, ATSScoreResult

logger = logging.getLogger(__name__)


class ResumeTailorService:
    def __init__(self) -> None:
        self.ats_scorer = ATSScorerService()

    def tailor(
        self,
        master_resume: str,
        tailored: TailoringResult,
        job_title: str = "",
        job_description: str = "",
    ) -> Tuple[str, int]:
        updated = master_resume

        if tailored.summary:
            updated = self._replace_section(updated, "Summary", tailored.summary)

        if tailored.skills:
            updated = self._merge_skills(updated, tailored.skills)

        if not job_description:
            return updated, 0

        ats = self.ats_scorer.score(updated, job_title, job_description)
        logger.info(
            "ATS score initial: %d%% (hard=%d soft=%d title=%d exp=%d edu=%d fmt=%d)",
            ats.overall_score, ats.hard_skill_score, ats.soft_skill_score,
            ats.title_score, ats.experience_score, ats.education_score,
            ats.format_score,
        )

        if ats.overall_score < 80 and ats.missing_keywords:
            updated = self._boost_keywords(updated, ats, job_title)
            ats = self.ats_scorer.score(updated, job_title, job_description)
            logger.info("ATS score after boost: %d%%", ats.overall_score)

        if ats.suggestions:
            for s in ats.suggestions:
                logger.info("ATS suggestion: %s", s)

        return updated, ats.overall_score

    def _merge_skills(self, markdown: str, new_skills: str) -> str:
        """Replace skills section content while preserving the section heading."""
        pattern = r"(## Skills\s*\n)(.*?)(?=\n## |\Z)"
        match = re.search(pattern, markdown, re.DOTALL)
        if match:
            return markdown[: match.start(2)] + new_skills + "\n" + markdown[match.end(2):]
        return markdown

    def _boost_keywords(
        self,
        markdown: str,
        ats: ATSScoreResult,
        job_title: str,
    ) -> str:
        """Inject missing keywords into skills section only — never touch experience."""
        missing = ats.missing_keywords[:8]
        if not missing:
            return markdown

        skills_match = re.search(r"(## Skills.*?)(\n## |\Z)", markdown, re.DOTALL)
        if skills_match:
            current = skills_match.group(1)
            additional = [kw.title() if len(kw) > 3 else kw.upper()
                          for kw in missing if kw.lower() not in current.lower()]
            if additional:
                new_skills = current.rstrip() + "\n\nATS Keywords: " + ", ".join(additional) + "\n"
                markdown = markdown.replace(current, new_skills)

        summary_match = re.search(r"(## Summary\s*\n)(.*?)(\n## |\Z)", markdown, re.DOTALL)
        if summary_match:
            summary_text = summary_match.group(2)
            title_words = set(re.findall(r"\w+", job_title.lower())) - {
                "the", "a", "an", "and", "or", "of", "for", "in", "at",
            }
            missing_title = [w for w in title_words if w not in summary_text.lower()]
            if missing_title and len(missing_title) <= 3:
                inject = " Experienced in " + ", ".join(w.title() for w in missing_title) + "."
                updated_summary = summary_text.rstrip() + inject + "\n"
                markdown = markdown[:summary_match.start(2)] + updated_summary + markdown[summary_match.end(2):]

        return markdown

    @staticmethod
    def _replace_section(markdown: str, section_name: str, new_content: str) -> str:
        pattern = rf"(## {re.escape(section_name)}\s*\n)(.*?)(?=\n## |\Z)"
        match = re.search(pattern, markdown, re.DOTALL)
        if match:
            return markdown[: match.start(2)] + new_content + "\n" + markdown[match.end(2):]
        return markdown + f"\n\n## {section_name}\n{new_content}\n"
