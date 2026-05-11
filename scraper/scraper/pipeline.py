"""Content processing pipeline for scraped meetings.

Downloads PDFs, extracts text (with OCR fallback), and normalizes
content before it is stored in the database.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import httpx
import structlog

from scraper.config import MAX_PDF_SIZE, REQUEST_TIMEOUT
from scraper.platforms.base import ScrapedMeeting, USER_AGENT
from scraper.processors.html import extract_html_text
from scraper.processors.pdf import extract_pdf_text, get_page_count
from scraper.processors.text import normalize_text

log = structlog.get_logger()


class ContentPipeline:
    """Download, extract, and normalize meeting minutes content.

    The pipeline operates on a single ScrapedMeeting at a time:

      1. If the meeting has a ``pdf_url``, download the PDF to
         ``storage_dir`` and extract text (with OCR fallback).
      2. Otherwise, if ``html_content`` is present, extract visible text.
      3. Normalize whatever text we obtained.

    The meeting object is mutated in-place and returned.
    """

    def __init__(self, storage_dir: str, skip_ocr: bool = False) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.skip_ocr = skip_ocr
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            verify=False,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def process(self, meeting: ScrapedMeeting) -> ScrapedMeeting:
        """Run the full content pipeline on a meeting."""
        # Step 1: Try PDF path
        if meeting.pdf_url:
            try:
                pdf_path = self._download_pdf(meeting)
                if pdf_path:
                    meeting.pdf_storage_path = str(pdf_path)
                    meeting.page_count = get_page_count(str(pdf_path))

                    text, ocr_applied = extract_pdf_text(str(pdf_path), skip_ocr=self.skip_ocr)
                    meeting.ocr_applied = ocr_applied

                    if text.strip():
                        meeting.raw_text = normalize_text(text)
                        return meeting
            except Exception:
                log.exception(
                    "pipeline.pdf_error",
                    pdf_url=meeting.pdf_url,
                    source_id=meeting.source_id,
                )

        # Step 2: Fall back to HTML extraction
        if meeting.html_content:
            try:
                html_text = extract_html_text(meeting.html_content)
                if html_text.strip():
                    meeting.raw_text = normalize_text(html_text)
                    return meeting
            except Exception:
                log.exception(
                    "pipeline.html_error",
                    source_id=meeting.source_id,
                )

        # Step 3: Normalize whatever raw_text already exists
        if meeting.raw_text:
            meeting.raw_text = normalize_text(meeting.raw_text)

        return meeting

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _download_pdf(self, meeting: ScrapedMeeting) -> Path | None:
        """Download a PDF from meeting.pdf_url to local storage.

        Returns the local path, or None on failure.  Uses a content-hash
        based filename to avoid duplicates.
        """
        url = meeting.pdf_url
        if not url:
            return None

        log.info("pipeline.download_pdf", url=url, source_id=meeting.source_id)

        try:
            resp = self.client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError:
            log.exception("pipeline.pdf_download_failed", url=url)
            return None

        content = resp.content

        if len(content) > MAX_PDF_SIZE:
            log.warning(
                "pipeline.pdf_too_large",
                url=url,
                size=len(content),
                max_size=MAX_PDF_SIZE,
            )
            return None

        # Build a deterministic filename: {date}_{source_id_hash}.pdf
        content_hash = hashlib.sha256(content).hexdigest()[:12]
        date_str = str(meeting.meeting_date) if meeting.meeting_date else "unknown"
        safe_date = date_str.replace("-", "")
        filename = f"{safe_date}_{content_hash}.pdf"

        # Organize by entity_id subdirectory
        entity_dir = self.storage_dir / f"entity_{meeting.source_id or 'unknown'}"
        entity_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = entity_dir / filename

        # Skip if already downloaded
        if pdf_path.exists() and pdf_path.stat().st_size == len(content):
            log.debug("pipeline.pdf_exists", path=str(pdf_path))
            return pdf_path

        pdf_path.write_bytes(content)
        log.info("pipeline.pdf_saved", path=str(pdf_path), size=len(content))
        return pdf_path
