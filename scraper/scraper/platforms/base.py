"""Abstract base scraper that all platform scrapers inherit from."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import httpx
import structlog

from scraper.config import REQUEST_TIMEOUT

log = structlog.get_logger()

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


@dataclass
class ScrapedMeeting:
    """Data collected for a single meeting's minutes."""

    title: str | None = None
    meeting_date: date | None = None
    committee_name: str | None = None
    meeting_type: str | None = None
    source_url: str | None = None
    source_id: str | None = None
    pdf_url: str | None = None
    html_content: str | None = None
    raw_text: str | None = None
    minutes_html: str | None = None
    minutes_text: str | None = None
    status: str = "HELD"
    ocr_applied: bool = False
    page_count: int | None = None
    pdf_storage_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for DB insertion."""
        return {
            "title": self.title,
            "meeting_date": self.meeting_date,
            "committee_name": self.committee_name,
            "meeting_type": self.meeting_type,
            "source_url": self.source_url,
            "source_id": self.source_id,
            "pdf_url": self.pdf_url,
            "html_content": self.html_content,
            "raw_text": self.raw_text,
            "minutes_html": self.minutes_html,
            "minutes_text": self.minutes_text,
            "status": self.status,
            "ocr_applied": self.ocr_applied,
            "page_count": self.page_count,
            "pdf_storage_path": self.pdf_storage_path,
        }


class BaseScraper(abc.ABC):
    """Abstract base class for platform-specific scrapers.

    Each platform (BoardDocs, Granicus, CivicPlus, etc.) implements a
    concrete subclass that knows how to navigate that platform's pages
    and APIs to retrieve meeting minutes.
    """

    def __init__(
        self,
        entity_id: str,
        minutes_url: str,
        platform_code: str | None = None,
        scrape_config: dict[str, Any] | None = None,
    ) -> None:
        self.entity_id = entity_id
        self.minutes_url = minutes_url
        self.platform_code = platform_code
        self.scrape_config = scrape_config or {}
        self.log = log.bind(
            entity_id=entity_id,
            platform=self.__class__.__name__,
        )
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            verify=False,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_meetings(self, since: date | None = None) -> list[ScrapedMeeting]:
        """Return a list of meetings (metadata only, no content yet).

        If *since* is provided, only return meetings on or after that date.
        """

    @abc.abstractmethod
    def get_minutes_content(self, meeting: ScrapedMeeting) -> ScrapedMeeting:
        """Populate the content fields of a ScrapedMeeting.

        Fetch the actual minutes text (HTML and/or PDF) and attach it to
        the meeting object.
        """

    # ------------------------------------------------------------------
    # Concrete orchestration
    # ------------------------------------------------------------------

    def scrape(self, since: date | None = None) -> list[ScrapedMeeting]:
        """Full scrape cycle: list meetings then fetch content for each.

        Returns the list of ScrapedMeeting objects with content populated.
        """
        self.log.info("scrape.start", since=str(since) if since else None)

        meetings = self.get_meetings(since=since)
        self.log.info("scrape.meetings_found", count=len(meetings))

        results: list[ScrapedMeeting] = []
        for idx, meeting in enumerate(meetings):
            try:
                self.log.debug(
                    "scrape.fetch_content",
                    meeting_title=meeting.title,
                    meeting_date=str(meeting.meeting_date),
                    progress=f"{idx + 1}/{len(meetings)}",
                )
                enriched = self.get_minutes_content(meeting)
                results.append(enriched)
            except Exception:
                self.log.exception(
                    "scrape.content_error",
                    meeting_source_id=meeting.source_id,
                    meeting_title=meeting.title,
                )
                # Still include the meeting with whatever metadata we have
                results.append(meeting)

        self.log.info("scrape.complete", total=len(results))
        return results
