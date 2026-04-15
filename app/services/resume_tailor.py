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
            updated = self._replace_section(updated, "Skills", tailored.skills)

        if tailored.experience_bullets:
            for section, bullets in tailored.experience_bullets.items():
                bullet_text = "\n".join(f"- {b}" for b in bullets)
                updated = self._replace_section(updated, section, bullet_text)

        if not job_description:
            return updated, 0

        ats = self.ats_scorer.score(updated, job_title, job_description)
        logger.info(
            "ATS score initial: %d%% (hard=%d soft=%d title=%d exp=%d)",
            ats.overall_score, ats.hard_skill_score, ats.soft_skill_score,
            ats.title_score, ats.experience_score,
        )

        if ats.overall_score < 80 and ats.missing_keywords:
            updated = self._boost_keywords(updated, ats, tailored, job_title)
            ats = self.ats_scorer.score(updated, job_title, job_description)
            logger.info("ATS score after boost: %d%%", ats.overall_score)

        if ats.suggestions:
            for s in ats.suggestions:
                logger.info("ATS suggestion: %s", s)

        return updated, ats.overall_score

    def _boost_keywords(
        self,
        markdown: str,
        ats: ATSScoreResult,
        tailored: TailoringResult,
        job_title: str,
    ) -> str:
        missing = ats.missing_keywords[:8]
        if not missing:
            return markdown

        skills_section = re.search(r"(## Skills.*?)(\n## |\Z)", markdown, re.DOTALL)
        if skills_section:
            current = skills_section.group(1)
            additional = ", ".join(kw.title() for kw in missing if kw.lower() not in current.lower())
            if additional:
                new_skills = current.rstrip() + ", " + additional + "\n"
                markdown = markdown.replace(current, new_skills)

        summary_section = re.search(r"(## Summary.*?)(\n## |\Z)", markdown, re.DOTALL)
        if summary_section:
            current = summary_section.group(1)
            title_words = set(job_title.lower().split()) - {"the", "a", "an", "and", "or"}
            missing_title = [w for w in title_words if w not in current.lower()]
            if missing_title:
                inject = " Experienced in " + ", ".join(missing_title) + "."
                lines = current.split("\n")
                if len(lines) >= 2:
                    lines[-1] = lines[-1].rstrip() + inject
                    markdown = markdown.replace(current, "\n".join(lines))

        return markdown

    @staticmethod
    def _replace_section(markdown: str, section_name: str, new_content: str) -> str:
        pattern = rf"(## {re.escape(section_name)}\s*\n)(.*?)(?=\n## |\Z)"
        match = re.search(pattern, markdown, re.DOTALL)
        if match:
            return markdown[: match.start(2)] + new_content + "\n" + markdown[match.end(2) :]
        return markdown + f"\n\n## {section_name}\n{new_content}\n"
