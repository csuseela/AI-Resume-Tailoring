from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ResumeLoaderService:
    def __init__(self, resume_dir: Path, source: str = "local", gdrive_file_id: str = "", gdrive_api_key: str = "") -> None:
        self.resume_dir = resume_dir
        self.source = source
        self.gdrive_file_id = gdrive_file_id
        self.gdrive_api_key = gdrive_api_key

    def load(self) -> str:
        if self.source == "gdrive" and self.gdrive_file_id:
            return self._load_from_gdrive()
        return self._load_local()

    def _load_local(self) -> str:
        # Prefer .md — it has proper markdown structure that the tailoring
        # pipeline and docx_writer both depend on. The docx_writer generates
        # a professional Word document from the tailored markdown output.
        md_files = list(self.resume_dir.glob("*.md"))
        if md_files:
            text = md_files[0].read_text(encoding="utf-8")
            logger.info("Loaded .md resume: %s (%d chars)", md_files[0].name, len(text))
            return text

        docx_files = list(self.resume_dir.glob("*.docx"))
        if docx_files:
            try:
                return self._read_docx(docx_files[0])
            except Exception as exc:
                logger.warning("Failed to read .docx (%s)", exc)

        txt_files = list(self.resume_dir.glob("*.txt"))
        if txt_files:
            text = txt_files[0].read_text(encoding="utf-8")
            logger.info("Loaded .txt resume: %s (%d chars)", txt_files[0].name, len(text))
            return text

        raise FileNotFoundError(f"No resume found in {self.resume_dir}")

    def _read_docx(self, path: Path) -> str:
        try:
            from docx import Document
            doc = Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            logger.info("Loaded .docx resume: %s (%d chars)", path.name, len(text))
            return text
        except ImportError:
            logger.warning("python-docx not installed")
            raise FileNotFoundError("python-docx not available and no .md found")

    def _load_from_gdrive(self) -> str:
        import requests
        url = f"https://www.googleapis.com/drive/v3/files/{self.gdrive_file_id}?alt=media&key={self.gdrive_api_key}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        logger.info("Loaded resume from Google Drive (%d bytes)", len(resp.content))
        return resp.text
