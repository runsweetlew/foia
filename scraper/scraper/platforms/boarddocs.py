"""Scraper for BoardDocs meeting management platform.

BoardDocs exposes an internal AJAX API that returns meeting lists and
agenda content.  The base URL pattern for Michigan entities is:

    https://go.boarddocs.com/mi/{code}/Board.nsf

Where {code} is the district/entity shortcode (e.g. "aaesa", "detroitk12").

BoardDocs has multiple product tiers:
  - BoardDocs Pro (boardType=1): Full committee support
  - BoardDocs LT  (boardType=2): Committee support, JSON meeting lists
  - BoardDocs PL  (boardType=3): May or may not have committees;
    boards with committee_available=0 are policy-only (no meetings)

For boards with committees, we use BD-GetMeetingsList (JSON).
As a fallback, we try BD-GETMeetingsListForSEO (GET, JSON).
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import httpx
import structlog

from scraper.platforms.base import BaseScraper, ScrapedMeeting

log = structlog.get_logger()

BOARDDOCS_BASE = "https://go.boarddocs.com/mi/{code}/Board.nsf"

# Delay between API requests to avoid CloudFront rate limiting
_REQUEST_DELAY = 1.5

# Headers matching what the browser sends for AJAX calls
AJAX_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not-A.Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-requested-with": "XMLHttpRequest",
    "origin": "https://go.boarddocs.com",
}


class BoardDocsScraper(BaseScraper):
    """Scraper for the BoardDocs platform.

    Expects either:
      - scrape_config["boarddocs_code"] to be set, OR
      - the minutes_url to contain the code as a path segment
        (e.g. https://go.boarddocs.com/mi/aaesa/Board.nsf)
    """

    def __init__(self, entity_id, minutes_url, platform_code=None, scrape_config=None):
        super().__init__(entity_id, minutes_url, platform_code, scrape_config)
        self.code = self._resolve_code()
        self.base_url = BOARDDOCS_BASE.format(code=self.code)
        self.public_url = f"{self.base_url}/Public"
        self.log = self.log.bind(boarddocs_code=self.code)
        self._committee_ids: list[str] | None = None
        # Override the base client with browser-like headers to avoid CloudFront blocks
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://go.boarddocs.com/",
            },
            timeout=30,
            follow_redirects=True,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_code(self) -> str:
        """Determine the BoardDocs district code."""
        code = self.scrape_config.get("boarddocs_code")
        if code:
            return code

        parsed = urlparse(self.minutes_url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "mi":
            return parts[1]

        raise ValueError(
            f"Cannot determine BoardDocs code from URL {self.minutes_url!r} "
            f"and no boarddocs_code in scrape_config"
        )

    def _discover_committee_ids(self) -> list[str]:
        """Fetch the public page and extract committee IDs from the HTML."""
        if self._committee_ids is not None:
            return self._committee_ids

        # Check scrape_config first
        configured = self.scrape_config.get("committee_id")
        if configured:
            self._committee_ids = [configured]
            return self._committee_ids

        url = f"{self.base_url}/Public"
        self.log.debug("boarddocs.discover_committees", url=url)
        resp = self.client.get(url)
        # BoardDocs PL boards return 403 but still have valid page content
        if resp.status_code == 403 and "BoardDocs" in resp.text:
            self.log.debug("boarddocs.403_with_content", url=url)
        elif resp.status_code != 200:
            resp.raise_for_status()
        time.sleep(_REQUEST_DELAY)

        # Detect board type and committee availability
        self._board_type = None
        self._committee_available = False
        bt_match = re.search(r'boardType="(\d+)"', resp.text)
        if bt_match:
            self._board_type = int(bt_match.group(1))
        ca_match = re.search(r'committee_available=(\d+)', resp.text)
        if ca_match:
            self._committee_available = int(ca_match.group(1)) > 0

        # Extract committeeid attributes from committee trigger links
        ids = re.findall(r'committeeid="([A-Z0-9]+)"', resp.text)
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_ids: list[str] = []
        for cid in ids:
            if cid not in seen:
                seen.add(cid)
                unique_ids.append(cid)

        if not unique_ids:
            if not self._committee_available:
                self.log.info(
                    "boarddocs.policy_only_board",
                    board_type=self._board_type,
                )
            else:
                self.log.warning("boarddocs.no_committees_found")

        self._committee_ids = unique_ids
        self.log.info(
            "boarddocs.committees_discovered",
            count=len(unique_ids),
            ids=unique_ids,
            board_type=self._board_type,
        )
        return self._committee_ids

    def _post(self, path: str, data: str = "") -> Any:
        """Make a POST request to a BoardDocs AJAX endpoint."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {
            **AJAX_HEADERS,
            "referer": f"{self.base_url}/Public",
        }
        self.log.debug("boarddocs.post", url=url)
        resp = self.client.post(url, content=data, headers=headers)
        # BoardDocs sometimes returns 403 but still has valid JSON/content
        if resp.status_code == 403 and resp.text.strip():
            self.log.debug("boarddocs.post_403_with_content", url=url)
            return resp
        resp.raise_for_status()
        return resp

    @staticmethod
    def _parse_numberdate(numberdate: str | int | None) -> date | None:
        """Parse the BoardDocs numberdate field into a Python date.

        BoardDocs stores dates as YYYYMMDD integer strings in the
        ``numberdate`` JSON field.
        """
        if numberdate is None:
            return None

        s = str(numberdate).strip()
        if not s:
            return None

        # Primary format: YYYYMMDD
        if len(s) == 8 and s.isdigit():
            try:
                return datetime.strptime(s, "%Y%m%d").date()
            except ValueError:
                pass

        # Fallback: other string formats
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue

        log.warning("boarddocs.date_parse_fail", raw=numberdate)
        return None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_meetings(self, since: date | None = None) -> list[ScrapedMeeting]:
        """Fetch the list of meetings from BoardDocs.

        Strategy:
        1. Discover committee IDs from the public page.
        2. If committees exist, call BD-GetMeetingsList for each.
        3. If no committees (policy-only PL boards), try the SEO endpoint
           as a last resort.
        """
        committee_ids = self._discover_committee_ids()

        if not committee_ids:
            # Try SEO endpoint as fallback (works without committee IDs)
            meetings = self._get_meetings_seo(since)
            if meetings:
                return meetings
            self.log.info("boarddocs.no_meetings_available")
            return []

        all_meetings: list[ScrapedMeeting] = []
        seen_ids: set[str] = set()

        for committee_id in committee_ids:
            form_data = f"current_committee_id={committee_id}"
            resp = self._post("BD-GetMeetingsList?open", data=form_data)
            time.sleep(_REQUEST_DELAY)

            if not resp.text.strip():
                self.log.warning("boarddocs.empty_meetings_response", committee_id=committee_id)
                continue

            try:
                payload = resp.json()
            except json.JSONDecodeError:
                self.log.error("boarddocs.meetings_json_error", body=resp.text[:500])
                continue

            items = payload if isinstance(payload, list) else payload.get("data", [])

            for item in items:
                unique_id = item.get("unique")
                if not unique_id:
                    continue

                # Skip empty placeholder items
                if not item.get("name") and not item.get("numberdate"):
                    continue

                # Deduplicate across committees
                if unique_id in seen_ids:
                    continue
                seen_ids.add(unique_id)

                meeting_date = self._parse_numberdate(item.get("numberdate"))

                if since and meeting_date and meeting_date < since:
                    continue

                # Determine meeting status based on date
                if meeting_date and meeting_date > date.today():
                    status = "SCHEDULED"
                else:
                    status = "HELD"

                meeting = ScrapedMeeting(
                    title=item.get("name") or item.get("title") or "Meeting",
                    meeting_date=meeting_date,
                    committee_name=committee_id,
                    meeting_type="Regular",
                    source_url=f"{self.base_url}/Public?open&id={unique_id}",
                    source_id=unique_id,
                    status=status,
                )
                all_meetings.append(meeting)

        self.log.info("boarddocs.meetings_parsed", count=len(all_meetings))
        return all_meetings

    def _get_meetings_seo(self, since: date | None = None) -> list[ScrapedMeeting]:
        """Fetch meetings from the SEO endpoint (no committee ID needed).

        BD-GETMeetingsListForSEO is a GET endpoint that returns JSON with
        keys: Name, Description, Unique, Date.
        """
        url = f"{self.base_url}/BD-GETMeetingsListForSEO?open"
        self.log.debug("boarddocs.seo_endpoint", url=url)

        try:
            resp = self.client.get(url)
            if resp.status_code not in (200, 403):
                resp.raise_for_status()
            time.sleep(_REQUEST_DELAY)
        except Exception:
            self.log.debug("boarddocs.seo_endpoint_failed")
            return []

        if not resp.text.strip() or len(resp.text.strip()) < 5:
            return []

        try:
            items = resp.json()
        except json.JSONDecodeError:
            return []

        if not isinstance(items, list):
            return []

        meetings: list[ScrapedMeeting] = []
        for item in items:
            unique_id = item.get("Unique")
            if not unique_id:
                continue

            name = item.get("Name") or "Meeting"
            date_str = item.get("Date")
            meeting_date = None
            if date_str:
                try:
                    meeting_date = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    ).date()
                except (ValueError, TypeError):
                    meeting_date = self._parse_numberdate(date_str)

            if since and meeting_date and meeting_date < since:
                continue

            if meeting_date and meeting_date > date.today():
                status = "SCHEDULED"
            else:
                status = "HELD"

            meetings.append(ScrapedMeeting(
                title=name,
                meeting_date=meeting_date,
                meeting_type="Regular",
                source_url=f"{self.base_url}/Public?open&id={unique_id}",
                source_id=unique_id,
                status=status,
            ))

        self.log.info("boarddocs.seo_meetings_parsed", count=len(meetings))
        return meetings

    def get_minutes_content(self, meeting: ScrapedMeeting) -> ScrapedMeeting:
        """Fetch the detailed agenda/minutes content for a single meeting.

        Uses PRINT-AgendaDetailed to get a full HTML rendering of the
        meeting minutes.  Also scans for PDF attachment links.
        """
        if not meeting.source_id:
            self.log.warning("boarddocs.no_source_id", title=meeting.title)
            return meeting

        committee_id = meeting.committee_name or ""
        form_data = f"id={meeting.source_id}&current_committee_id={committee_id}"
        resp = self._post("PRINT-AgendaDetailed", data=form_data)
        time.sleep(_REQUEST_DELAY)

        html = resp.text
        meeting.html_content = html

        soup = BeautifulSoup(html, "lxml")

        # Try to get a better committee name from the HTML
        name_div = soup.find("div", {"class": "print-meeting-name"})
        if name_div and name_div.string:
            meeting.committee_name = name_div.string.strip()

        pdf_url = self._find_pdf_link(soup)
        if pdf_url:
            meeting.pdf_url = pdf_url

        for tag in soup.find_all(["script", "style", "nav"]):
            tag.decompose()

        meeting.raw_text = soup.get_text(separator="\n").strip()

        return meeting

    def get_actual_minutes(self, meeting: ScrapedMeeting) -> ScrapedMeeting:
        """Fetch actual approved meeting minutes via BD-GetMinutes.

        BD-GetMinutes returns empty string for future/unapproved meetings
        and substantial HTML (39KB-777KB) for approved ones.
        """
        if not meeting.source_id:
            self.log.debug("boarddocs.skip_minutes_no_id", title=meeting.title)
            return meeting

        if meeting.status == "SCHEDULED":
            return meeting

        committee_id = meeting.committee_name or ""
        form_data = f"id={meeting.source_id}&current_committee_id={committee_id}"
        resp = self._post("BD-GetMinutes", data=form_data)
        time.sleep(_REQUEST_DELAY)

        html = resp.text.strip()

        # BD-GetMinutes returns empty or very short string for unapproved meetings
        if not html or len(html) < 100:
            self.log.debug("boarddocs.no_minutes", source_id=meeting.source_id)
            return meeting

        meeting.minutes_html = html
        meeting.status = "APPROVED"

        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["script", "style", "nav"]):
            tag.decompose()
        meeting.minutes_text = soup.get_text(separator="\n").strip()

        self.log.info(
            "boarddocs.minutes_fetched",
            source_id=meeting.source_id,
            size=len(html),
        )
        return meeting

    def get_budget_documents(self) -> list[dict]:
        """Fetch budget-related documents from the BoardDocs public file library."""
        try:
            resp = self._post("BD-GetPublicFiles")
        except Exception:
            self.log.debug("boarddocs.no_public_files")
            return []

        if not resp.text.strip():
            return []

        try:
            payload = resp.json()
        except json.JSONDecodeError:
            self.log.debug("boarddocs.public_files_json_error")
            return []

        items = payload if isinstance(payload, list) else payload.get("data", [])

        budget_keywords = [
            "budget", "financial", "audit", "cafr", "fiscal",
            "expenditure", "revenue", "appropriation", "millage",
        ]
        budget_docs = []
        for item in items:
            name = (item.get("name") or item.get("title") or "").strip()
            name_lower = name.lower()
            if not any(kw in name_lower for kw in budget_keywords):
                continue

            url = item.get("url") or item.get("link") or ""
            if url:
                url = self._make_absolute(url)

            budget_docs.append({
                "title": name,
                "type": "BUDGET",
                "source_url": url,
                "pdf_url": url if url.lower().endswith(".pdf") else None,
                "fiscal_year": self._extract_fiscal_year(name),
            })

        self.log.info("boarddocs.budget_docs_found", count=len(budget_docs))
        return budget_docs

    @staticmethod
    def _extract_fiscal_year(name: str) -> str | None:
        """Try to extract a fiscal year from a document name."""
        # Match patterns like "2024-2025", "2024-25", "FY2024", "FY 2024"
        m = re.search(r"(\d{4})\s*[-–]\s*(\d{2,4})", name)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
        m = re.search(r"(?:FY\s*)?(\d{4})", name)
        if m:
            return m.group(1)
        return None

    def _find_pdf_link(self, soup: BeautifulSoup) -> str | None:
        """Scan parsed HTML for links to PDF attachments."""
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = (link.get_text() or "").lower()

            if href.lower().endswith(".pdf"):
                if "minute" in text:
                    return self._make_absolute(href)

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf"):
                return self._make_absolute(href)

        return None

    def _make_absolute(self, url: str) -> str:
        """Ensure a URL is absolute, resolving against the base URL."""
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(self.base_url, url)
