from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(
        self,
        template_dir: Path,
        output_dir: Path,
        *,
        enabled: bool = False,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        email_to: str = "",
    ) -> None:
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.enabled = enabled
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_to = email_to
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def send_summary(self, rows: List[Dict[str, Any]], run_id: int) -> Path:
        html = self._render(rows, run_id)
        preview_path = self._save_preview(html)

        if self.enabled and self.smtp_user and self.smtp_password:
            self._send_smtp(html, run_id)

        return preview_path

    def _render(self, rows: List[Dict[str, Any]], run_id: int) -> str:
        template = self.env.get_template("email_summary.html")
        return template.render(
            rows=rows,
            run_id=run_id,
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            total=len(rows),
        )

    def _save_preview(self, html: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        path = self.output_dir / f"email_preview_{date_str}.html"
        path.write_text(html, encoding="utf-8")
        logger.info("Email preview saved: %s", path)
        return path

    def _send_smtp(self, html: str, run_id: int) -> None:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"AI Resume Tailoring — Daily Summary (Run #{run_id})"
            msg["From"] = self.smtp_user
            msg["To"] = self.email_to
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, self.email_to.split(","), msg.as_string())
            logger.info("Email sent to %s", self.email_to)
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
