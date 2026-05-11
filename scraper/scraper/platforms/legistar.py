"""Scraper for Legistar / Granicus meeting management platform.

Legistar provides a free, unauthenticated REST API at:

    https://webapi.legistar.com/v1/{client}/

Where {client} is the municipality or entity code (e.g. "detroit",
"chicago", "washtenawcounty").

Common endpoints used:
  - GET /events          -- list meetings/events
  - GET /events/{id}     -- single event detail

The API supports OData-style query parameters for filtering, ordering,
and pagination.
"""

from __future__ import annotations

import re
import time
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import structlog

from scraper.platforms.base import BaseScraper, ScrapedMeeting

log = structlog.get_logger()

LEGISTAR_API_BASE = "https://webapi.legistar.com/v1/{client}"

# Maximum number of results per API request (Legistar default is 1000)
PAGE_SIZE = 1000

# Rate-limit delay between paginated API requests (seconds)
API_DELAY = 0.5


class LegistarScraper(BaseScraper):
    """Scraper for the Legistar / Granicus platform.

    Expects one of the following to identify the Legistar client code:
      - scrape_config["legistar_client"] explicitly set, OR
      - platform_code set to the client code, OR
      - the minutes_url containing the client code in one of:
            {client}.legistar.com
            webapi.legistar.com/v1/{client}/
    """

    def __init__(self, entity_id, minutes_url, platform_code=None, scrape_config=None):
        super().__init__(entity_id, minutes_url, platform_code, scrape_config)
        self.legistar_client = self._resolve_client()
        self.api_base = LEGISTAR_API_BASE.format(client=self.legistar_client)
        self.log = self.log.bind(legistar_client=self.legistar_client)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_client(self) -> str:
        """Determine the Legistar client code from config or URL."""
        # 1. Explicit config
        client = self.scrape_config.get("legistar_client")
        if client:
            return client.strip().lower()

        # 2. platform_code
        if self.platform_code:
            return self.platform_code.strip().lower()

        # 3. Extract from minutes_url
        url = self.minutes_url or ""

        # Pattern: {client}.legistar.com
        m = re.search(r"(\w[\w-]*)\.legistar\.com", url, re.IGNORECASE)
        if m:
            candidate = m.group(1).lower()
            # Skip the 'webapi' subdomain -- that needs path extraction
            if candidate != "webapi":
                return candidate

        # Pattern: webapi.legistar.com/v1/{client}/
        m = re.search(r"webapi\.legistar\.com/v1/(\w[\w-]*)", url, re.IGNORECASE)
        if m:
            return m.group(1).lower()

        # Pattern: {client}.granicus.com or similar Granicus URLs
        m = re.search(r"(\w[\w-]*)\.granicus\.com", url, re.IGNORECASE)
        if m:
            candidate = m.group(1).lower()
            if candidate not in ("www", "api"):
                return candidate

        raise ValueError(
            f"Cannot determine Legistar client code from URL {self.minutes_url!r} "
            f"and no legistar_client in scrape_config"
        )

    def _api_get(self, path: str, params: dict[str, str] | None = None) -> Any:
        """Make a GET request to the Legistar API.

        Returns the parsed JSON response.
        """
        url = f"{self.api_base}/{path.lstrip('/')}"
        self.log.debug("legistar.api_get", url=url, params=params)
        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _get_all_events(
        self,
        since: date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all events from the Legistar API, handling pagination.

        Legistar uses OData-style $top and $skip for pagination.
        """
        params: dict[str, str] = {
            "$orderby": "EventDate desc",
            "$top": str(PAGE_SIZE),
        }

        if since:
            date_str = since.strftime("%Y-%m-%d")
            params["$filter"] = f"EventDate ge datetime'{date_str}'"

        all_events: list[dict[str, Any]] = []
        skip = 0

        while True:
            if skip > 0:
                params["$skip"] = str(skip)
            elif "$skip" in params:
                del params["$skip"]

            try:
                events = self._api_get("events", params=params)
            except Exception:
                self.log.exception(
                    "legistar.events_request_error",
                    skip=skip,
                )
                break

            if not isinstance(events, list):
                self.log.warning(
                    "legistar.unexpected_response_type",
                    response_type=type(events).__name__,
                )
                break

            if not events:
                break

            all_events.extend(events)
            self.log.debug(
                "legistar.events_page",
                count=len(events),
                total=len(all_events),
                skip=skip,
            )

            # If we got fewer than PAGE_SIZE results, we have everything
            if len(events) < PAGE_SIZE:
                break

            skip += PAGE_SIZE
            time.sleep(API_DELAY)

        return all_events

    @staticmethod
    def _parse_event_date(event: dict[str, Any]) -> date | None:
        """Parse the EventDate field from a Legistar event.

        Legistar returns dates in ISO-like format:
        "2024-01-15T00:00:00" or "2024-01-15T18:30:00".
        """
        raw = event.get("EventDate")
        if not raw:
            return None

        if isinstance(raw, str):
            # Strip trailing timezone info if present
            raw = raw.split("+")[0].split("Z")[0]
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    continue

        log.warning("legistar.date_parse_fail", raw=raw)
        return None

    @staticmethod
    def _determine_status(event: dict[str, Any], meeting_date: date | None) -> str:
        """Determine meeting status from Legistar event fields.

        - "APPROVED" if EventMinutesStatusName is "Final"
        - "SCHEDULED" if the meeting date is in the future
        - "HELD" otherwise
        """
        minutes_status = (event.get("EventMinutesStatusName") or "").strip()
        if minutes_status == "Final":
            return "APPROVED"

        if meeting_date and meeting_date > date.today():
            return "SCHEDULED"

        return "HELD"

    def _build_source_url(self, event: dict[str, Any]) -> str | None:
        """Build the public-facing URL for an event.

        Prefers EventInSiteURL; falls back to constructing a Legistar URL.
        """
        in_site_url = event.get("EventInSiteURL")
        if in_site_url:
            return in_site_url

        # Fallback: construct URL from client and event ID
        event_id = event.get("EventId")
        if event_id:
            return (
                f"https://{self.legistar_client}.legistar.com/"
                f"MeetingDetail.aspx?ID={event_id}&GUID=0"
            )
        return None

    def _event_to_meeting(self, event: dict[str, Any]) -> ScrapedMeeting:
        """Convert a Legistar event dict to a ScrapedMeeting."""
        meeting_date = self._parse_event_date(event)
        status = self._determine_status(event, meeting_date)

        # Prefer minutes PDF over agenda PDF
        minutes_file = event.get("EventMinutesFile") or None
        agenda_file = event.get("EventAgendaFile") or None
        pdf_url = minutes_file or agenda_file

        body_name = event.get("EventBodyName") or None
        event_id = event.get("EventId")

        # Build a descriptive title
        title_parts = []
        if body_name:
            title_parts.append(body_name)
        event_time = event.get("EventTime")
        if event_time:
            title_parts.append(f"({event_time})")
        title = " ".join(title_parts) if title_parts else "Meeting"

        return ScrapedMeeting(
            title=title,
            meeting_date=meeting_date,
            committee_name=body_name,
            meeting_type=event.get("EventBodyName"),
            source_url=self._build_source_url(event),
            source_id=str(event_id) if event_id is not None else None,
            pdf_url=pdf_url,
            status=status,
        )

    # ------------------------------------------------------------------
    # Public interface -- BaseScraper implementation
    # ------------------------------------------------------------------

    def get_meetings(self, since: date | None = None) -> list[ScrapedMeeting]:
        """Fetch the list of meetings from the Legistar events API.

        Calls GET /events with optional date filtering and handles
        pagination transparently.
        """
        self.log.info("legistar.get_meetings", since=str(since) if since else None)

        events = self._get_all_events(since=since)
        self.log.info("legistar.events_fetched", count=len(events))

        meetings: list[ScrapedMeeting] = []
        seen_ids: set[str] = set()

        for event in events:
            event_id = event.get("EventId")
            if event_id is None:
                continue

            source_id = str(event_id)
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)

            try:
                meeting = self._event_to_meeting(event)
                meetings.append(meeting)
            except Exception:
                self.log.exception(
                    "legistar.event_parse_error",
                    event_id=event_id,
                )

        self.log.info("legistar.meetings_parsed", count=len(meetings))
        return meetings

    def get_minutes_content(self, meeting: ScrapedMeeting) -> ScrapedMeeting:
        """Populate content fields for a ScrapedMeeting.

        If the meeting already has a pdf_url, returns it as-is (the
        ContentPipeline in main.py handles PDF download and text
        extraction).

        If no PDF is available, attempts to fetch the event's web page
        and extract text content from the HTML.
        """
        if meeting.pdf_url:
            self.log.debug(
                "legistar.has_pdf",
                source_id=meeting.source_id,
                pdf_url=meeting.pdf_url,
            )
            return meeting

        # No PDF -- try to scrape the event web page for content
        if meeting.source_url:
            try:
                self.log.debug(
                    "legistar.fetch_event_page",
                    source_id=meeting.source_id,
                    url=meeting.source_url,
                )
                resp = self.client.get(meeting.source_url)
                resp.raise_for_status()

                html = resp.text
                meeting.html_content = html

                soup = BeautifulSoup(html, "html.parser")

                # Remove script/style/nav noise
                for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
                    tag.decompose()

                # Look for PDF links on the page
                pdf_url = self._find_pdf_link(soup)
                if pdf_url:
                    meeting.pdf_url = pdf_url
                    self.log.debug(
                        "legistar.found_pdf_on_page",
                        source_id=meeting.source_id,
                        pdf_url=pdf_url,
                    )

                # Extract text content
                meeting.raw_text = soup.get_text(separator="\n", strip=True)

            except Exception:
                self.log.exception(
                    "legistar.event_page_error",
                    source_id=meeting.source_id,
                    url=meeting.source_url,
                )

        return meeting

    def get_actual_minutes(self, meeting: ScrapedMeeting) -> ScrapedMeeting:
        """Try to fetch the actual minutes PDF if not already available.

        Re-checks the event detail API endpoint for an EventMinutesFile
        that may not have been present when get_meetings initially ran
        (e.g., minutes approved after the event list was cached).
        """
        if not meeting.source_id:
            self.log.debug("legistar.skip_minutes_no_id", title=meeting.title)
            return meeting

        if meeting.status == "SCHEDULED":
            return meeting

        # If we already have a minutes PDF (not just agenda), skip
        # We re-check the API to see if minutes have been posted
        try:
            event = self._api_get(f"events/{meeting.source_id}")
        except Exception:
            self.log.debug(
                "legistar.minutes_detail_error",
                source_id=meeting.source_id,
            )
            return meeting

        if not isinstance(event, dict):
            return meeting

        minutes_file = event.get("EventMinutesFile")
        minutes_status = (event.get("EventMinutesStatusName") or "").strip()

        if minutes_file:
            meeting.pdf_url = minutes_file
            self.log.info(
                "legistar.minutes_found",
                source_id=meeting.source_id,
                pdf_url=minutes_file,
            )

            if minutes_status == "Final":
                meeting.status = "APPROVED"

        elif minutes_status == "Final":
            # Minutes are marked final but no file -- check for inline content
            meeting.status = "APPROVED"
            self.log.debug(
                "legistar.minutes_final_no_file",
                source_id=meeting.source_id,
            )

        return meeting

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def _find_pdf_link(self, soup: BeautifulSoup) -> str | None:
        """Scan parsed HTML for links to PDF files.

        Prefers links with 'minute' in the link text; falls back to any
        PDF link found.
        """
        # First pass: look for PDF links mentioning minutes
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = (link.get_text() or "").lower()
            if href.lower().endswith(".pdf") and "minute" in text:
                return self._make_absolute(href)

        # Second pass: any PDF link
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf"):
                return self._make_absolute(href)

        return None

    def _make_absolute(self, url: str) -> str:
        """Ensure a URL is absolute."""
        if url.startswith(("http://", "https://")):
            return url

        # Resolve relative to the Legistar site
        base = f"https://{self.legistar_client}.legistar.com/"
        if url.startswith("/"):
            parsed = urlparse(base)
            return f"{parsed.scheme}://{parsed.netloc}{url}"
        return base + url
