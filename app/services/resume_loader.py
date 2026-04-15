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
        docx_files = list(self.resume_dir.glob("*.docx"))
        if docx_files:
            try:
                return self._read_docx(docx_files[0])
            except Exception as exc:
                logger.warning("Failed to read .docx (%s), falling back to .md", exc)

        md_files = list(self.resume_dir.glob("*.md"))
        if md_files:
            return md_files[0].read_text(encoding="utf-8")

        txt_files = list(self.resume_dir.glob("*.txt"))
        if txt_files:
            return txt_files[0].read_text(encoding="utf-8")

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
            logger.warning("python-docx not installed, falling back to .md")
            return self._load_local_md_only()

    def _load_local_md_only(self) -> str:
        md_files = list(self.resume_dir.glob("*.md"))
        if md_files:
            return md_files[0].read_text(encoding="utf-8")
        raise FileNotFoundError(f"No .md resume found in {self.resume_dir}")

    def _load_from_gdrive(self) -> str:
        import requests
        url = f"https://www.googleapis.com/drive/v3/files/{self.gdrive_file_id}?alt=media&key={self.gdrive_api_key}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        logger.info("Loaded resume from Google Drive (%d bytes)", len(resp.content))
        return resp.text
