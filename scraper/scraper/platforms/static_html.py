"""Scraper for entities that post meeting minutes as PDF links on their website.

Handles the "long tail" of municipalities that don't use a commercial platform
like BoardDocs or Legistar.  Common patterns include:

- WordPress sites with a "Minutes" or "Meetings" page listing PDF downloads
- Township/city .gov sites with an archive of board meeting PDFs
- Pages with HTML tables or unordered lists of dates linked to PDF files

The scraper fetches the configured ``minutes_url``, finds all ``<a>`` tags
linking to ``.pdf`` files, scores them for relevance (meeting-related keywords),
extracts dates from the link text or filename, and builds a
:class:`ScrapedMeeting` for each qualifying link.

Optional ``scrape_config`` keys:

``css_selector``
    CSS selector to narrow the search area on the page (e.g.
    ``"#minutes-archive a"``).
``follow_links``
    If *True*, also follow sub-page links whose text contains "minutes"
    and scrape PDF links from those pages.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
import httpx
import structlog

from scraper.platforms.base import BaseScraper, ScrapedMeeting

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Keyword scoring
# ---------------------------------------------------------------------------

_STRONG_KEYWORDS: list[str] = [
    "minutes",
    "meeting minutes",
]

_MEDIUM_KEYWORDS: list[str] = [
    "meeting",
    "board",
    "council",
    "commission",
    "agenda",
    "township",
    "village",
    "trustee",
    "selectmen",
    "selectboard",
]

_SKIP_KEYWORDS: list[str] = [
    "budget",
    "newsletter",
    "report",
    "application",
    "form",
    "ordinance",
    "zoning map",
    "annual",
    "financial statement",
    "audit",
    "receipt",
    "invoice",
    "strategic plan",
    "training",
    "holiday",
    "calendar",
    "schedule",
    "charter",
    "handbook",
    "brochure",
    "flyer",
    "directory",
    "roster",
    "complaint",
    "policy",
    "by-laws",
    "bylaws",
    "contract",
    "bid",
    "rfp",
    "resume",
    "job posting",
    "employment",
    "recreation",
    "pollinator",
    "vacation",
    "property check",
    "utility",
    "water quality",
    "consumer confidence",
    "school district map",
    "improvement notice",
]

# ---------------------------------------------------------------------------
# Document keywords (master plans, budgets, etc.)
# ---------------------------------------------------------------------------

_MASTER_PLAN_KEYWORDS: list[str] = [
    "master plan",
    "masterplan",
    "master-plan",
    "comprehensive plan",
    "comp plan",
    "future land use",
    "land use plan",
]

_BUDGET_KEYWORDS: list[str] = [
    "budget",
    "annual budget",
    "adopted budget",
    "proposed budget",
    "fiscal year budget",
]

# ---------------------------------------------------------------------------
# Document type classification (agenda vs minutes)
# ---------------------------------------------------------------------------

_AGENDA_KEYWORDS: list[str] = [
    "agenda",
    "upcoming",
    "notice of meeting",
    "meeting notice",
    "public notice",
    "posted agenda",
]

_MINUTES_KEYWORDS: list[str] = [
    "minutes",
    "approved minutes",
    "draft minutes",
    "unapproved minutes",
    "meeting minutes",
    "regular minutes",
    "special minutes",
]

# ---------------------------------------------------------------------------
# Meeting type classification
# ---------------------------------------------------------------------------

_SPECIAL_KEYWORDS: list[str] = [
    "special",
    "emergency",
    "called",
    "special meeting",
    "emergency meeting",
]

_WORK_SESSION_KEYWORDS: list[str] = [
    "work session",
    "workshop",
    "study session",
    "committee of the whole",
]

_PUBLIC_HEARING_KEYWORDS: list[str] = [
    "public hearing",
    "hearing",
    "truth in taxation",
    "budget hearing",
]

_ORGANIZATIONAL_KEYWORDS: list[str] = [
    "organizational",
    "re-organization",
    "reorganization",
    "sine die",
    "inaugural",
]

# ---------------------------------------------------------------------------
# Date extraction patterns
# ---------------------------------------------------------------------------

# Order matters: more specific patterns first.
_DATE_PATTERNS: list[tuple[str, str]] = [
    # "January 15, 2024" / "Jan 15, 2024"
    (
        r"(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
        r"\.?\s+\d{1,2},?\s+\d{4}",
        "_parse_human_date",
    ),
    # ISO "2024-01-15"
    (r"\d{4}-\d{1,2}-\d{1,2}", "_parse_iso_date"),
    # US with slashes "01/15/2024"
    (r"\d{1,2}/\d{1,2}/\d{4}", "_parse_us_slash_date"),
    # US with dashes "01-15-2024"
    (r"\d{1,2}-\d{1,2}-\d{4}", "_parse_us_dash_date"),
    # Short year "1-15-24" or "01.15.24"
    (r"\d{1,2}[.\-]\d{1,2}[.\-]\d{2}(?!\d)", "_parse_short_year_date"),
    # Filename-embedded year+month "minutes_2024-01" or "2024_01_board"
    (r"\d{4}[_\-]\d{1,2}", "_parse_year_month"),
]

# Compiled once for performance.
_COMPILED_DATE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pat, re.IGNORECASE), method) for pat, method in _DATE_PATTERNS
]

# ---------------------------------------------------------------------------
# Pagination link detection
# ---------------------------------------------------------------------------

_PAGINATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"next\s*page", re.IGNORECASE),
    re.compile(r"older\s*(entries|posts)?", re.IGNORECASE),
    re.compile(r"^(?:next|>>?|›)$", re.IGNORECASE),
    re.compile(r"page\s+\d+", re.IGNORECASE),
]


# ===================================================================
# Scraper
# ===================================================================


class StaticHtmlScraper(BaseScraper):
    """Scraper for entities that post meeting minutes as PDF links on their website."""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    # Common subpaths where school boards post meeting minutes.
    _BOARD_SUBPATHS: list[str] = [
        "/board-of-education/meeting-minutes",
        "/board-of-education/meetings",
        "/board-of-education/board-meetings",
        "/board-of-education/minutes",
        "/board/meetings",
        "/board/minutes",
        "/board/board-meetings",
        "/board/meeting-minutes",
        "/our-district/board-of-education",
        "/our-district/board/minutes",
        "/district/board-of-education",
        "/about/board-of-education",
        "/about/board",
        "/about/board/meetings",
        "/about/meetings",
        "/about/boe/meeting-minutes",
        "/meetings",
        "/minutes",
        "/meeting-minutes",
        "/agendas-minutes",
        "/agendas-and-minutes",
        "/board-meetings",
        "/board-of-education",
    ]

    def get_meetings(self, since: date | None = None) -> list[ScrapedMeeting]:
        """Fetch the minutes page and extract meeting PDF links.

        Parameters
        ----------
        since:
            If provided, only return meetings on or after this date.
        """
        all_meetings: list[ScrapedMeeting] = []
        seen_urls: set[str] = set()

        # Scrape the primary minutes page.
        self._scrape_page(
            self.minutes_url,
            all_meetings,
            seen_urls,
            since,
        )

        # Follow one level of pagination.
        pagination_urls = self._find_pagination_links(self.minutes_url)
        for page_url in pagination_urls:
            if page_url in seen_urls:
                continue
            self.log.debug("static_html.follow_pagination", url=page_url)
            self._scrape_page(page_url, all_meetings, seen_urls, since)

        # Optionally follow sub-page links containing "minutes" in their text.
        if self.scrape_config.get("follow_links"):
            sub_urls = self._find_minutes_subpages(self.minutes_url)
            for sub_url in sub_urls:
                if sub_url in seen_urls:
                    continue
                self.log.debug("static_html.follow_subpage", url=sub_url)
                self._scrape_page(sub_url, all_meetings, seen_urls, since)

        # If we found nothing, auto-probe common board subpaths on the same domain.
        if not all_meetings:
            self._probe_board_subpaths(all_meetings, seen_urls, since)

        # Sort by date descending (None-dated items go last).
        all_meetings.sort(
            key=lambda m: m.meeting_date or date.min,
            reverse=True,
        )

        self.log.info("static_html.meetings_found", count=len(all_meetings))
        return all_meetings

    def _probe_board_subpaths(
        self,
        results: list[ScrapedMeeting],
        seen_urls: set[str],
        since: date | None,
    ) -> None:
        """When the primary URL yields no meetings, try common subpaths."""
        parsed = urlparse(self.minutes_url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"

        self.log.debug("static_html.probing_subpaths", domain=parsed.netloc)

        for subpath in self._BOARD_SUBPATHS:
            sub_url = base_origin + subpath
            if sub_url in seen_urls:
                continue

            before = len(results)
            self._scrape_page(sub_url, results, seen_urls, since)

            if len(results) > before:
                self.log.info(
                    "static_html.subpath_hit",
                    subpath=subpath,
                    meetings=len(results) - before,
                )
                # Also follow links on this successful subpath
                sub_links = self._find_minutes_subpages(sub_url)
                for link_url in sub_links:
                    if link_url in seen_urls:
                        continue
                    self._scrape_page(link_url, results, seen_urls, since)
                break  # Found a working subpath, stop probing

    def get_minutes_content(self, meeting: ScrapedMeeting) -> ScrapedMeeting:
        """Return the meeting as-is.

        The ``pdf_url`` is already set and the downstream ContentPipeline
        handles PDF download and text extraction.
        """
        return meeting

    def get_documents(self) -> list[dict]:
        """Scrape the minutes page for master plans and budget documents.

        Returns a list of dicts with keys matching ``upsert_document()``
        expectations: title, type, sourceUrl, pdfUrl, fiscalYear.
        """
        documents: list[dict] = []
        seen_urls: set[str] = set()

        # Scrape the primary page and any pagination.
        for url in [self.minutes_url] + self._find_pagination_links(self.minutes_url):
            self._scrape_documents_from_page(url, documents, seen_urls)

        # Also follow sub-pages if configured.
        if self.scrape_config.get("follow_links"):
            for sub_url in self._find_minutes_subpages(self.minutes_url):
                if sub_url not in seen_urls:
                    self._scrape_documents_from_page(sub_url, documents, seen_urls)

        if documents:
            self.log.info("static_html.documents_found", count=len(documents))
        return documents

    def _scrape_documents_from_page(
        self,
        url: str,
        results: list[dict],
        seen_urls: set[str],
    ) -> None:
        """Find master plan and budget PDFs on a page."""
        html = self._fetch_page(url)
        if html is None:
            return

        soup = BeautifulSoup(html, "lxml")
        pdf_links = [
            a for a in soup.find_all("a", href=True)
            if a["href"].strip().lower().endswith(".pdf")
        ]

        for link in pdf_links:
            href = link["href"].strip()
            abs_url = self._make_absolute(href, url)
            if abs_url in seen_urls:
                continue

            link_text = self._clean_text(link.get_text())
            combined = f"{link_text} {href}".lower()

            doc_type = self._classify_doc_type(combined)
            if doc_type is None:
                continue

            seen_urls.add(abs_url)

            # Try to extract a year from the text/filename.
            fiscal_year = self._extract_fiscal_year(combined)

            title = link_text or self._title_from_filename(href)

            results.append({
                "title": title,
                "type": doc_type,
                "sourceUrl": url,
                "pdfUrl": abs_url,
                "fiscalYear": fiscal_year,
            })

    @staticmethod
    def _classify_doc_type(text: str) -> str | None:
        """Check if text matches a document type we want to capture."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in _MASTER_PLAN_KEYWORDS):
            return "MASTER_PLAN"
        if any(kw in text_lower for kw in _BUDGET_KEYWORDS):
            return "BUDGET"
        return None

    @staticmethod
    def _extract_fiscal_year(text: str) -> str | None:
        """Try to extract a 4-digit year from text."""
        m = re.search(r"20[12]\d", text)
        return m.group(0) if m else None

    # ------------------------------------------------------------------
    # Page scraping
    # ------------------------------------------------------------------

    def _scrape_page(
        self,
        url: str,
        results: list[ScrapedMeeting],
        seen_urls: set[str],
        since: date | None,
    ) -> None:
        """Fetch *url*, find PDF links, score and filter them, and append
        qualifying :class:`ScrapedMeeting` objects to *results*.
        """
        html = self._fetch_page(url)
        if html is None:
            return

        soup = BeautifulSoup(html, "lxml")

        # Optionally narrow the search area via CSS selector.
        css_selector = self.scrape_config.get("css_selector")
        if css_selector:
            containers = soup.select(css_selector)
            if not containers:
                self.log.warning(
                    "static_html.css_selector_empty",
                    selector=css_selector,
                    url=url,
                )
                # Fall back to the whole page.
                search_root: Tag | BeautifulSoup = soup
            else:
                # Wrap matches in a new soup so find_all works uniformly.
                wrapper = BeautifulSoup("<div></div>", "lxml").div
                assert wrapper is not None
                for c in containers:
                    wrapper.append(c.extract())
                search_root = wrapper
        else:
            search_root = soup

        # Find all <a> tags whose href ends in .pdf (case-insensitive).
        pdf_links: list[Tag] = [
            a
            for a in search_root.find_all("a", href=True)
            if a["href"].strip().lower().endswith(".pdf")
        ]

        self.log.debug(
            "static_html.pdf_links_found",
            count=len(pdf_links),
            url=url,
        )

        for link in pdf_links:
            href: str = link["href"].strip()
            abs_url = self._make_absolute(href, url)

            if abs_url in seen_urls:
                continue

            link_text = self._clean_text(link.get_text())
            combined_text = f"{link_text} {href}".lower()

            # --- Score the link -------------------------------------------
            score = self._score_link(combined_text)
            if score <= 0:
                self.log.debug(
                    "static_html.skip_link",
                    reason="negative_score",
                    text=link_text[:80],
                    url=abs_url,
                )
                continue

            # --- Extract date ---------------------------------------------
            meeting_date = self._extract_date(link_text, href)

            # Filter by since.
            if since and meeting_date and meeting_date < since:
                continue

            seen_urls.add(abs_url)

            source_id = hashlib.md5(abs_url.encode()).hexdigest()[:16]

            title = link_text or self._title_from_filename(href)
            status, meeting_type = self._classify_document(combined_text)

            meeting = ScrapedMeeting(
                title=title,
                meeting_date=meeting_date,
                meeting_type=meeting_type,
                pdf_url=abs_url,
                source_url=url,
                source_id=source_id,
                status=status,
            )
            results.append(meeting)

    # ------------------------------------------------------------------
    # Link scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _score_link(text: str) -> int:
        """Score a PDF link for meeting-minutes relevance.

        Returns a positive score for likely minutes, 0 for neutral, and a
        negative score for links that should be skipped.
        """
        text_lower = text.lower()

        # Check skip keywords first.
        for kw in _SKIP_KEYWORDS:
            if kw in text_lower:
                # If a skip keyword co-occurs with a strong keyword, don't skip.
                has_strong = any(sk in text_lower for sk in _STRONG_KEYWORDS)
                if not has_strong:
                    return -1

        score = 0
        for kw in _STRONG_KEYWORDS:
            if kw in text_lower:
                score += 10
        for kw in _MEDIUM_KEYWORDS:
            if kw in text_lower:
                score += 3

        return score

    # ------------------------------------------------------------------
    # Document type classification
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_document(text: str) -> tuple[str, str]:
        """Classify a PDF link as agenda or minutes and determine meeting type.

        Returns (status, meeting_type) where:
        - status is "APPROVED" for minutes, "SCHEDULED" for agendas
        - meeting_type is "Regular", "Special", "Work Session", etc.
        """
        text_lower = text.lower()

        # --- Determine if this is an agenda or minutes ---
        has_agenda = any(kw in text_lower for kw in _AGENDA_KEYWORDS)
        has_minutes = any(kw in text_lower for kw in _MINUTES_KEYWORDS)

        if has_minutes and not has_agenda:
            status = "APPROVED"
        elif has_agenda and not has_minutes:
            status = "HELD"  # Agendas aren't approved minutes
        elif has_agenda and has_minutes:
            # Both present — "minutes" wins (e.g. "minutes and agenda packet")
            status = "APPROVED"
        else:
            # Neither keyword — default based on whether title/filename
            # looks more like minutes or agenda
            status = "APPROVED"

        # --- Determine meeting type ---
        if any(kw in text_lower for kw in _SPECIAL_KEYWORDS):
            meeting_type = "Special"
        elif any(kw in text_lower for kw in _WORK_SESSION_KEYWORDS):
            meeting_type = "Work Session"
        elif any(kw in text_lower for kw in _PUBLIC_HEARING_KEYWORDS):
            meeting_type = "Public Hearing"
        elif any(kw in text_lower for kw in _ORGANIZATIONAL_KEYWORDS):
            meeting_type = "Organizational"
        else:
            meeting_type = "Regular"

        return status, meeting_type

    # ------------------------------------------------------------------
    # Date extraction
    # ------------------------------------------------------------------

    def _extract_date(self, link_text: str, href: str) -> date | None:
        """Try to extract a meeting date from link text or the PDF filename.

        Tries the link text first (more likely to be a clean human-readable
        date), then falls back to the href/filename.
        """
        for source in (link_text, href):
            if not source:
                continue
            result = self._try_parse_date(source)
            if result is not None:
                return result
        return None

    def _try_parse_date(self, text: str) -> date | None:
        """Apply all date regex patterns against *text* and return the first
        successful parse, or ``None``.
        """
        for pattern, method_name in _COMPILED_DATE_PATTERNS:
            m = pattern.search(text)
            if m:
                parser = getattr(self, method_name)
                result = parser(m.group(0))
                if result is not None:
                    return result
        return None

    # --- Individual date parsers ------------------------------------------

    @staticmethod
    def _parse_human_date(s: str) -> date | None:
        """Parse 'January 15, 2024' / 'Jan 15, 2024' style dates."""
        # Normalise: remove trailing period from abbreviated month, ensure comma.
        s = s.strip().replace("Sept ", "Sep ")
        for fmt in (
            "%B %d, %Y",
            "%B %d %Y",
            "%b %d, %Y",
            "%b %d %Y",
            "%b. %d, %Y",
            "%b. %d %Y",
        ):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_iso_date(s: str) -> date | None:
        """Parse '2024-01-15'."""
        try:
            return datetime.strptime(s.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_us_slash_date(s: str) -> date | None:
        """Parse '01/15/2024'."""
        try:
            return datetime.strptime(s.strip(), "%m/%d/%Y").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_us_dash_date(s: str) -> date | None:
        """Parse '01-15-2024'."""
        try:
            return datetime.strptime(s.strip(), "%m-%d-%Y").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_short_year_date(s: str) -> date | None:
        """Parse '1-15-24' or '01.15.24'."""
        # Normalise the separator to '-'.
        normalised = s.strip().replace(".", "-")
        try:
            return datetime.strptime(normalised, "%m-%d-%y").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_year_month(s: str) -> date | None:
        """Parse year-month fragment like '2024-01' (default to 1st of month)."""
        normalised = s.strip().replace("_", "-")
        try:
            return datetime.strptime(normalised, "%Y-%m").date()
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def _find_pagination_links(self, page_url: str) -> list[str]:
        """Return URLs of pagination links (next page, older posts, etc.)
        found on the page at *page_url*.  Only follows one level deep.
        """
        html = self._fetch_page(page_url)
        if html is None:
            return []

        soup = BeautifulSoup(html, "lxml")
        pagination_urls: list[str] = []

        for a_tag in soup.find_all("a", href=True):
            link_text = self._clean_text(a_tag.get_text())
            if not link_text:
                continue
            for pat in _PAGINATION_PATTERNS:
                if pat.search(link_text):
                    abs_url = self._make_absolute(a_tag["href"].strip(), page_url)
                    if abs_url != page_url and abs_url not in pagination_urls:
                        pagination_urls.append(abs_url)
                    break

        self.log.debug(
            "static_html.pagination_links",
            count=len(pagination_urls),
            urls=pagination_urls[:5],
        )
        return pagination_urls

    # ------------------------------------------------------------------
    # Sub-page following
    # ------------------------------------------------------------------

    def _find_minutes_subpages(self, page_url: str) -> list[str]:
        """Find links on *page_url* whose text contains 'minutes' and that
        link to HTML pages (not PDFs).  Used when ``follow_links`` is enabled.
        """
        html = self._fetch_page(page_url)
        if html is None:
            return []

        soup = BeautifulSoup(html, "lxml")
        subpage_urls: list[str] = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            # Skip PDFs -- those are handled by the main scraper logic.
            if href.lower().endswith(".pdf"):
                continue
            link_text = self._clean_text(a_tag.get_text()).lower()
            if "minute" in link_text:
                abs_url = self._make_absolute(href, page_url)
                if abs_url != page_url and abs_url not in subpage_urls:
                    subpage_urls.append(abs_url)

        self.log.debug(
            "static_html.subpage_links",
            count=len(subpage_urls),
            urls=subpage_urls[:5],
        )
        return subpage_urls

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _fetch_page(self, url: str) -> str | None:
        """Fetch *url* and return HTML text, or ``None`` on failure."""
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPStatusError as exc:
            self.log.warning(
                "static_html.http_error",
                url=url,
                status=exc.response.status_code,
            )
        except httpx.TimeoutException:
            self.log.warning("static_html.timeout", url=url)
        except httpx.RequestError as exc:
            self.log.warning(
                "static_html.request_error",
                url=url,
                error=str(exc),
            )
        return None

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_absolute(href: str, base_url: str) -> str:
        """Resolve *href* against *base_url* to produce an absolute URL."""
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(base_url, href)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Collapse whitespace and strip surrounding blanks."""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _title_from_filename(href: str) -> str:
        """Derive a human-readable title from a PDF filename."""
        path = urlparse(href).path
        filename = path.rsplit("/", 1)[-1] if "/" in path else path
        # Remove extension.
        name = filename.rsplit(".", 1)[0] if "." in filename else filename
        # Replace separators with spaces.
        name = re.sub(r"[_\-]+", " ", name)
        return name.strip().title() or "Meeting Minutes"
