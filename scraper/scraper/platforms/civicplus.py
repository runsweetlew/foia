"""Scraper for CivicPlus AgendaCenter platform.

CivicPlus AgendaCenter pages list meetings with links to agenda and
minutes PDFs.  The URL pattern for minutes is:

    /AgendaCenter/ViewFile/Minutes/_MMDDYYYY-{id}

which returns a PDF directly.  The main listing page at /AgendaCenter
shows meetings grouped by category (committee) with year filtering.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import structlog

from scraper.platforms.base import BaseScraper, ScrapedMeeting

log = structlog.get_logger()

# Regex for AgendaCenter ViewFile links
# Matches: /AgendaCenter/ViewFile/(Minutes|Agenda)/_MMDDYYYY-ID
_VIEWFILE_RE = re.compile(
    r"/AgendaCenter/ViewFile/(Minutes|Agenda)/_?(\d{8})-(\d+)",
    re.IGNORECASE,
)

# Regex for meeting date in MMDDYYYY format
_DATE_MMDDYYYY = re.compile(r"^(\d{2})(\d{2})(\d{4})$")


class CivicPlusScraper(BaseScraper):
    """Scraper for CivicPlus AgendaCenter sites."""

    def get_meetings(self, since: date | None = None) -> list[ScrapedMeeting]:
        """Parse the AgendaCenter page for meeting minutes links."""
        url = self.minutes_url
        if not url:
            return []

        # Ensure we're hitting the AgendaCenter page
        if not url.rstrip("/").lower().endswith("agendacenter"):
            # Try appending /AgendaCenter
            parsed = urlparse(url)
            if "agendacenter" not in parsed.path.lower():
                url = urljoin(url.rstrip("/") + "/", "AgendaCenter")

        self.log.info("civicplus.fetch_page", url=url)

        try:
            resp = self.client.get(url)
            resp.raise_for_status()
        except Exception:
            self.log.exception("civicplus.page_error", url=url)
            return []

        html = resp.text
        base_url = str(resp.url)

        # Parse all ViewFile links
        meetings_by_id: dict[str, dict] = {}

        for match in _VIEWFILE_RE.finditer(html):
            file_type = match.group(1).lower()  # "minutes" or "agenda"
            date_str = match.group(2)  # MMDDYYYY
            meeting_id = match.group(3)  # numeric ID

            meeting_date = _parse_mmddyyyy(date_str)
            if since and meeting_date and meeting_date < since:
                continue

            if meeting_id not in meetings_by_id:
                meetings_by_id[meeting_id] = {
                    "id": meeting_id,
                    "date_str": date_str,
                    "meeting_date": meeting_date,
                    "agenda_path": None,
                    "minutes_path": None,
                }

            full_path = match.group(0)
            if file_type == "minutes":
                meetings_by_id[meeting_id]["minutes_path"] = full_path
            elif file_type == "agenda":
                meetings_by_id[meeting_id]["agenda_path"] = full_path

        # Also try to extract meeting titles from surrounding HTML
        title_map = self._extract_titles(html)

        # Build ScrapedMeeting objects — only for meetings that have minutes
        results: list[ScrapedMeeting] = []
        for mid, info in meetings_by_id.items():
            minutes_path = info.get("minutes_path")
            if not minutes_path:
                continue  # Only scrape meetings that have minutes

            pdf_url = urljoin(base_url, minutes_path)
            source_id = hashlib.sha256(
                f"civicplus_{mid}_{info['date_str']}".encode()
            ).hexdigest()[:16]

            title = title_map.get(mid, "Board Meeting")

            meeting = ScrapedMeeting(
                title=title,
                meeting_date=info["meeting_date"],
                meeting_type="Regular",
                source_url=base_url,
                source_id=source_id,
                pdf_url=pdf_url,
                status="APPROVED",
            )
            results.append(meeting)

        self.log.info(
            "civicplus.meetings_found",
            total_viewfiles=len(meetings_by_id),
            with_minutes=len(results),
        )
        return results

    def get_minutes_content(self, meeting: ScrapedMeeting) -> ScrapedMeeting:
        """Minutes content is a PDF — the pipeline handles download/extraction."""
        # pdf_url is already set from get_meetings; the ContentPipeline
        # will download and extract text from it.
        return meeting

    @staticmethod
    def _extract_titles(html: str) -> dict[str, str]:
        """Try to extract meeting titles from the HTML near ViewFile links.

        CivicPlus AgendaCenter typically shows the meeting title in the
        same row or section as the agenda/minutes links.  We look for
        text like "Board of Commissioners" or "Planning Commission" near
        the meeting ID.
        """
        titles: dict[str, str] = {}

        # Pattern: look for category/committee headers followed by meeting rows
        # The HTML structure varies by site, but typically has category sections
        # with meeting items inside.  We'll try to find the text near each link.
        for match in re.finditer(
            r'class="[^"]*catName[^"]*"[^>]*>([^<]+)',
            html,
            re.IGNORECASE,
        ):
            cat_name = match.group(1).strip()
            # Find meeting IDs near this category
            region_start = match.end()
            region = html[region_start : region_start + 5000]
            for vm in _VIEWFILE_RE.finditer(region):
                mid = vm.group(3)
                if mid not in titles:
                    titles[mid] = cat_name

        return titles


def _parse_mmddyyyy(date_str: str) -> date | None:
    """Parse a MMDDYYYY date string into a date object."""
    m = _DATE_MMDDYYYY.match(date_str)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None
