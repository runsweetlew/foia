"""
Discover meeting minutes pages by probing candidate URLs directly.

Instead of using a search engine, this script generates plausible website
URLs from entity names (e.g. "Springfield Township" -> springfieldtwp.org),
tests which ones resolve, then crawls the live site for meeting-minutes
pages.  Platform detection (BoardDocs, Granicus, CivicPlus, etc.) matches
the logic used by discover_google.py.

Usage:
    python -m discover_urls [--type TOWNSHIP] [--limit 100] [--workers 15]
    python -m discover_urls --type VILLAGE --dry-run
"""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import httpx

from scraper.db import get_connection, get_cursor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Short timeout -- we're probing thousands of URLs; most bad ones should
# fail within 3-5 seconds.
PROBE_TIMEOUT = 5.0
CRAWL_TIMEOUT = 8.0

# Subpaths to crawl once we find a live domain.
MINUTES_SUBPATHS = [
    "/meetings",
    "/minutes",
    "/agendas",
    "/agendas-minutes",
    "/agendas-and-minutes",
    "/board",
    "/council",
    "/board-meetings",
    "/board-of-trustees",
    "/meeting-minutes",
    "/government/meetings",
    "/government/minutes",
    "/government/agendas-minutes",
    "/city-council",
    "/city-council/minutes",
    "/city-council/agendas-minutes",
    "/village-council",
    "/village-council/minutes",
    "/township-board",
    "/township-board/minutes",
    "/board-of-education",
    "/board-of-education/meetings",
    "/board/meetings",
    "/board/board-meetings",
    "/AgendaCenter",
    "/agendacenter",
    "/public-meetings",
    "/meeting-archive",
    "/meeting-calendar",
    "/about/meetings",
    "/about/minutes",
]

# Platform detection -- URL patterns
PLATFORM_URL_PATTERNS: dict[str, list[str]] = {
    "BOARDDOCS":        [r"boarddocs\.com"],
    "GRANICUS":         [r"legistar\.com", r"granicus\.com"],
    "CIVICPLUS_AGENDA": [r"/agendacenter", r"/AgendaCenter", r"civicplus\.com"],
    "CIVICCLERK":       [r"civicclerk\.com"],
    "IQM2":             [r"iqm2\.com"],
    "CIVICWEB":         [r"civicweb\.net"],
    "PRIMEGOV":         [r"primegov\.com"],
}

# Platform detection -- body markers (substring match, lowercased)
PLATFORM_BODY_MARKERS: dict[str, list[str]] = {
    "BOARDDOCS":        ["boarddocs"],
    "GRANICUS":         ["granicus", "legistar"],
    "CIVICCLERK":       ["civicclerk"],
    "CIVICPLUS_AGENDA": ["civicplus", "agendacenter"],
    "IQM2":             ["iqm2"],
    "PRIMEGOV":         ["primegov"],
}

# Link-text keywords used when scanning a homepage for minutes links.
LINK_KEYWORDS = [
    "meeting minutes", "board minutes", "council minutes",
    "minutes", "agendas & minutes", "agendas and minutes",
    "board meetings", "council meetings", "board of education",
    "public meetings", "meeting archive", "meeting calendar",
    "agenda center", "boarddocs", "legistar",
]

# URL-path keywords used when scoring links.
URL_PATH_KEYWORDS = [
    "minutes", "agenda", "meeting", "boarddocs", "legistar",
    "granicus", "civicclerk", "agendacenter",
    "board-meetings", "board_meetings",
    "council-meetings", "public-meetings",
]


# ---------------------------------------------------------------------------
# URL generation
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Lowercase, strip non-alphanumeric (keep spaces), collapse spaces."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def generate_candidate_domains(name: str, entity_type: str) -> list[str]:
    """Return a list of candidate domain names (no scheme) for an entity.

    The caller will prepend ``https://`` and ``https://www.`` to each one.
    """
    clean = _slugify(name)
    words = clean.split()
    if not words:
        return []

    domains: list[str] = []

    if entity_type == "TOWNSHIP":
        # "Springfield Township" -> words = ["springfield", "township"]
        # or entity name might already be "Springfield" with type=TOWNSHIP
        base_words = [w for w in words if w != "township"]
        if not base_words:
            base_words = words
        base = "".join(base_words)          # springfield
        base_hyp = "-".join(base_words)     # spring-field (multi-word)

        domains += [
            f"{base}township.org",
            f"{base}twp.org",
            f"{base}twpmi.org",
            f"{base}townshipmi.org",
            f"{base}-township.org",
            f"{base}township.com",
            f"{base}twp.com",
            f"{base}twpmi.com",
            f"{base}townshipmi.com",
            f"{base}-township.com",
            f"{base}township.net",
            f"{base}twp.net",
            f"{base}townshipmi.gov",
            f"{base}twp.us",
            f"{base}-twp.org",
        ]
        if base_hyp != base:
            domains += [
                f"{base_hyp}township.org",
                f"{base_hyp}-township.org",
                f"{base_hyp}twp.org",
            ]

    elif entity_type == "VILLAGE":
        base_words = [w for w in words if w not in ("village", "of")]
        if not base_words:
            base_words = words
        base = "".join(base_words)
        base_hyp = "-".join(base_words)

        domains += [
            f"villageof{base}.com",
            f"villageof{base}.org",
            f"{base}village.com",
            f"{base}village.org",
            f"{base}mi.org",
            f"{base}mi.com",
            f"{base}.org",
            f"{base}.com",
            f"villageof{base}.net",
            f"{base}villagemi.org",
            f"village-of-{base_hyp}.org",
        ]

    elif entity_type == "CITY":
        base_words = [w for w in words if w not in ("city", "of")]
        if not base_words:
            base_words = words
        base = "".join(base_words)
        base_hyp = "-".join(base_words)

        domains += [
            f"cityof{base}.org",
            f"cityof{base}.com",
            f"{base}mi.org",
            f"{base}mi.com",
            f"{base}city.org",
            f"{base}city.com",
            f"{base}.org",
            f"{base}.com",
            f"ci.{base}.mi.us",
            f"{base}mi.gov",
            f"cityof{base}.net",
            f"city-of-{base_hyp}.org",
        ]

    elif entity_type == "COUNTY":
        base_words = [w for w in words if w != "county"]
        if not base_words:
            base_words = words
        base = "".join(base_words)

        domains += [
            f"{base}countymi.gov",
            f"co.{base}.mi.us",
            f"{base}county.org",
            f"{base}county.com",
            f"{base}county.net",
            f"{base}countymi.org",
            f"{base}countygovernment.com",
        ]

    elif entity_type in ("SCHOOL_DISTRICT", "ISD"):
        # Strip common suffixes
        strip_suffixes = [
            "intermediate school district",
            "community schools",
            "public schools",
            "area schools",
            "school district",
            "schools",
            "charter school",
            "charter academy",
            "academy",
        ]
        stripped = clean
        for suf in strip_suffixes:
            if stripped.endswith(suf):
                stripped = stripped[: -len(suf)].strip()
                break
        sw = stripped.split() or words
        base = "".join(sw)
        base_hyp = "-".join(sw)

        domains += [
            f"{base}.org",
            f"{base}.k12.mi.us",
            f"{base}schools.org",
            f"{base}schools.com",
            f"{base_hyp}.org",
        ]
        if entity_type == "ISD" and sw:
            domains += [
                f"{sw[0]}isd.org",
                f"{sw[0]}resa.org",
            ]
        elif sw:
            domains += [
                f"{sw[0]}schools.org",
                f"{sw[0]}.k12.mi.us",
            ]

    elif entity_type == "ROAD_COMMISSION":
        # "Alcona County Road Commission" -> words = ["alcona", "county", "road", "commission"]
        county_words = [w for w in words if w not in ("county", "road", "commission")]
        if not county_words:
            county_words = words[:1]
        county = "".join(county_words)

        domains += [
            f"{county}crc.com",
            f"{county}crc.org",
            f"{county}roads.com",
            f"{county}roads.org",
            f"{county}roadcommission.org",
            f"{county}roadcommission.com",
            f"{county}countyroads.com",
            f"{county}countyroads.org",
            f"{county}countyrc.org",
            f"crc{county}.org",
            f"{county}-roads.com",
            f"{county}countyroadcommission.org",
        ]

    elif entity_type == "COMMUNITY_COLLEGE":
        # Strip common suffixes
        strip_suffixes = [
            "community college", "college",
        ]
        stripped = clean
        for suf in strip_suffixes:
            if stripped.endswith(suf):
                stripped = stripped[: -len(suf)].strip()
                break
        sw = stripped.split() or words
        base = "".join(sw)

        domains += [
            f"{base}.edu",
            f"{base}cc.edu",
            f"{sw[0]}.edu",
            f"{sw[0]}cc.edu",
        ]

    elif entity_type == "UNIVERSITY":
        # Strip common suffixes
        strip_suffixes = [
            "university", "state university",
        ]
        stripped = clean
        for suf in strip_suffixes:
            if stripped.endswith(suf):
                stripped = stripped[: -len(suf)].strip()
                break
        sw = stripped.split() or words
        base = "".join(sw)
        initials = "".join(w[0] for w in sw) if len(sw) >= 2 else sw[0]

        domains += [
            f"{initials}.edu",
            f"{base}.edu",
            f"{sw[0]}.edu",
        ]

    else:
        # Generic fallback
        base = "".join(words)
        domains += [
            f"{base}.org",
            f"{base}.com",
            f"{base}mi.org",
            f"{base}mi.com",
        ]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for d in domains:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique


def expand_to_urls(domains: list[str]) -> list[str]:
    """Given bare domain names, return full URLs with https:// and www. variants."""
    urls: list[str] = []
    for d in domains:
        urls.append(f"https://www.{d}")
        urls.append(f"https://{d}")
    return urls


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platform_from_url(url: str) -> str | None:
    """Detect platform from URL string alone."""
    url_lower = url.lower()
    for platform, patterns in PLATFORM_URL_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, url_lower):
                return platform
    return None


def detect_platform_from_body(body: str) -> str | None:
    """Detect platform from page body (lowercased)."""
    for platform, markers in PLATFORM_BODY_MARKERS.items():
        for marker in markers:
            if marker in body:
                return platform
    return None


def check_page_for_minutes(url: str, body: str) -> dict | None:
    """Given a fetched page URL and body, detect if it is a minutes page.

    Returns a dict with ``platform`` and ``url`` keys, or None.
    """
    body_lower = body.lower()

    # 1. URL-based platform detection
    platform = detect_platform_from_url(url)
    if platform:
        return {"url": url, "platform": platform, "source": "url_pattern"}

    # 2. Body-based platform detection
    platform = detect_platform_from_body(body_lower)
    if platform:
        return {"url": url, "platform": platform, "source": "body_marker"}

    # 3. PDF heuristic -- 3+ PDF links + meeting keywords = STATIC_HTML
    pdf_count = len(re.findall(r'\.pdf["\'>\s?]', body_lower))
    meeting_kw_count = sum(
        1 for kw in ("minutes", "meeting", "agenda", "board")
        if kw in body_lower
    )
    if pdf_count >= 3 and meeting_kw_count >= 2:
        return {"url": url, "platform": "STATIC_HTML", "source": "pdf_heuristic"}

    return None


# ---------------------------------------------------------------------------
# Link scanning on a homepage
# ---------------------------------------------------------------------------

def find_minutes_links(html: str, base_url: str) -> list[dict]:
    """Scan an HTML page for links that look like they point to minutes."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        text = tag.get_text(strip=True).lower()
        href_lower = href.lower()
        abs_url = urljoin(base_url, href)

        score = 0

        # Text scoring
        for kw in LINK_KEYWORDS:
            if kw in text:
                score += 3
                break

        # URL path scoring
        for kw in URL_PATH_KEYWORDS:
            if kw in href_lower:
                score += 2
                break

        # Platform in URL is a strong signal
        plat = detect_platform_from_url(abs_url)
        if plat:
            score += 5

        if score >= 2:
            results.append({
                "url": abs_url,
                "text": tag.get_text(strip=True)[:100],
                "score": score,
                "platform": plat,
            })

    results.sort(key=lambda x: -x["score"])
    return results


# ---------------------------------------------------------------------------
# Core probing logic
# ---------------------------------------------------------------------------

def probe_entity(entity: dict) -> dict | None:
    """Probe candidate URLs for a single entity.

    Returns a result dict on success, None on failure.

    Strategy:
      1. Generate candidate domain names.
      2. Expand to full URLs (https:// and www. variants).
      3. Try each URL with a short HEAD/GET. Stop at first live site.
      4. On the live homepage, check for platform markers and scan links.
      5. Crawl well-known subpaths (/minutes, /meetings, ...).
      6. Follow the best minutes link and verify the target page.
    """
    entity_id = entity["id"]
    entity_name = entity["name"]
    entity_type = entity["type"]

    domains = generate_candidate_domains(entity_name, entity_type)
    if not domains:
        return None

    candidate_urls = expand_to_urls(domains)

    # Shared client for this entity -- keep-alive across requests to the
    # same host, but short timeouts.
    client = httpx.Client(
        headers=HEADERS,
        timeout=httpx.Timeout(PROBE_TIMEOUT, connect=3.0),
        follow_redirects=True,
        verify=False,           # many municipal sites have bad certs
    )

    try:
        # ------------------------------------------------------------------
        # Phase 1: find a live website
        # ------------------------------------------------------------------
        live_url: str | None = None
        homepage_html: str | None = None

        for url in candidate_urls:
            try:
                resp = client.get(url)
                if resp.status_code == 200 and len(resp.text) > 500:
                    live_url = str(resp.url)
                    homepage_html = resp.text
                    break
            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.TooManyRedirects,
                OSError,
            ):
                continue

        if not live_url or not homepage_html:
            return None

        # Reject false-positive domains
        final_domain = urlparse(live_url).netloc.lower()
        blocked_domains = {
            "google.com", "workspace.google.com", "calendar.google.com",
            "facebook.com", "twitter.com", "youtube.com", "linkedin.com",
            "instagram.com", "pinterest.com", "tiktok.com", "yelp.com",
            "wikipedia.org", "amazon.com", "apple.com", "microsoft.com",
            "squarespace.com", "wix.com", "godaddy.com", "wordpress.com",
            "govdelivery.com", "nextdoor.com",
        }
        for blocked in blocked_domains:
            if final_domain == blocked or final_domain.endswith("." + blocked):
                return None

        # ------------------------------------------------------------------
        # Phase 2: check homepage itself for platform markers
        # ------------------------------------------------------------------
        result = check_page_for_minutes(live_url, homepage_html)
        if result:
            return _build_result(entity, live_url, result["url"], result["platform"], "homepage")

        # ------------------------------------------------------------------
        # Phase 3: scan homepage links for minutes references
        # ------------------------------------------------------------------
        link_result = _follow_best_link(client, entity, live_url, homepage_html)
        if link_result:
            return link_result

        # ------------------------------------------------------------------
        # Phase 4: crawl well-known subpaths
        # ------------------------------------------------------------------
        parsed = urlparse(live_url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"

        # Bump timeout slightly for subpage fetches
        client.timeout = httpx.Timeout(CRAWL_TIMEOUT, connect=4.0)

        for subpath in MINUTES_SUBPATHS:
            sub_url = base_origin + subpath
            try:
                resp = client.get(sub_url)
                if resp.status_code != 200:
                    continue

                final_sub_url = str(resp.url)
                sub_result = check_page_for_minutes(final_sub_url, resp.text)
                if sub_result:
                    return _build_result(
                        entity, live_url, sub_result["url"],
                        sub_result["platform"], f"subpath:{subpath}",
                    )

                # Even if the subpage itself isn't definitively a minutes
                # page, check its links (one level deep).
                sub_link_result = _follow_best_link(client, entity, final_sub_url, resp.text)
                if sub_link_result:
                    return sub_link_result

            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.TooManyRedirects,
                OSError,
            ):
                continue

    finally:
        client.close()

    return None


def _follow_best_link(
    client: httpx.Client,
    entity: dict,
    page_url: str,
    page_html: str,
) -> dict | None:
    """Find the best minutes-looking link on *page_html* and follow it."""
    links = find_minutes_links(page_html, page_url)
    if not links:
        return None

    # Try the top 3 candidates at most
    for link in links[:3]:
        # If URL pattern already identifies the platform, accept immediately
        if link["platform"]:
            return _build_result(
                entity, page_url, link["url"],
                link["platform"], "link_on_page",
            )

        # Otherwise follow the link
        try:
            resp = client.get(link["url"])
            if resp.status_code != 200:
                continue

            final_url = str(resp.url)
            result = check_page_for_minutes(final_url, resp.text)
            if result:
                return _build_result(
                    entity, page_url, result["url"],
                    result["platform"], "followed_link",
                )
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.TooManyRedirects,
            OSError,
        ):
            continue

    return None


def _build_result(
    entity: dict,
    website_url: str,
    minutes_url: str,
    platform: str,
    source: str,
) -> dict:
    return {
        "entity_id": entity["id"],
        "entity_name": entity["name"],
        "entity_type": entity["type"],
        "county_name": entity.get("county_name"),
        "website_url": website_url,
        "minutes_url": minutes_url,
        "platform": platform,
        "source": source,
    }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def load_entities(entity_type: str | None = None, limit: int = 0) -> list[dict]:
    """Load entities that have no minutesUrl yet."""
    conn = get_connection()
    try:
        with get_cursor(conn) as cur:
            query = """
                SELECT e.id, e.name, e.type::text as type,
                       e.platform::text as platform,
                       c.name as county_name
                FROM "Entity" e
                LEFT JOIN "County" c ON e."countyId" = c.id
                WHERE (e."minutesUrl" IS NULL OR e."minutesUrl" = '')
            """
            params: list = []

            if entity_type:
                query += " AND e.type::text = %s"
                params.append(entity_type)

            query += " ORDER BY e.type, e.name"

            if limit > 0:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def save_results_to_db(results: list[dict]) -> int:
    """Persist discovered URLs to the Entity table. Returns count updated."""
    if not results:
        return 0

    conn = get_connection()
    updated = 0
    try:
        with get_cursor(conn) as cur:
            for r in results:
                cur.execute(
                    """
                    UPDATE "Entity"
                    SET platform = %s,
                        "minutesUrl" = %s,
                        "scrapeStatus" = 'PENDING',
                        "updatedAt" = NOW()
                    WHERE id = %s
                      AND ("minutesUrl" IS NULL OR "minutesUrl" = '')
                    """,
                    (r["platform"], r["minutes_url"], r["entity_id"]),
                )
                if cur.rowcount > 0:
                    updated += 1
        return updated
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    import warnings

    # Suppress InsecureRequestWarning from urllib3 since we use verify=False
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    parser = argparse.ArgumentParser(
        description="Discover meeting-minutes pages by probing candidate URLs",
    )
    parser.add_argument("--type", type=str, default=None,
                        help="Filter by entity type (TOWNSHIP, CITY, VILLAGE, COUNTY, SCHOOL_DISTRICT, ISD)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max entities to process (0 = all)")
    parser.add_argument("--workers", type=int, default=15,
                        help="Number of parallel workers (default: 15)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print results but do not update the database")
    args = parser.parse_args()

    entities = load_entities(entity_type=args.type, limit=args.limit)
    total = len(entities)
    print(f"Loaded {total} entities needing URL discovery")

    if not entities:
        print("Nothing to do.")
        return

    # Summary by type
    by_type: dict[str, int] = {}
    for e in entities:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c}")
    print()

    results: list[dict] = []
    errors = 0
    checked = 0
    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(probe_entity, e): e for e in entities}

        for future in as_completed(futures):
            checked += 1
            entity = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    elapsed = time.monotonic() - start_time
                    rate = checked / elapsed if elapsed > 0 else 0
                    print(
                        f"  [{checked:>4}/{total}] FOUND  "
                        f"{result['entity_name'][:40]:<40s} "
                        f"-> {result['platform']:<18s} "
                        f"{result['minutes_url'][:70]}  "
                        f"({rate:.1f}/s)"
                    )
                else:
                    if checked % 25 == 0 or checked == total:
                        elapsed = time.monotonic() - start_time
                        rate = checked / elapsed if elapsed > 0 else 0
                        print(
                            f"  [{checked:>4}/{total}] progress: "
                            f"{len(results)} found, {errors} errors  "
                            f"({rate:.1f} entities/s)"
                        )
            except Exception as exc:
                errors += 1
                print(f"  [{checked:>4}/{total}] ERROR  {entity['name']}: {exc}")

    elapsed = time.monotonic() - start_time

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'=' * 78}")
    print("URL DISCOVERY RESULTS")
    print(f"{'=' * 78}")
    print(f"  Checked:     {checked}")
    print(f"  Found:       {len(results)}")
    print(f"  Errors:      {errors}")
    print(f"  Elapsed:     {elapsed:.1f}s  ({checked / elapsed:.1f} entities/s)")
    print()

    by_platform: dict[str, int] = {}
    for r in results:
        by_platform[r["platform"]] = by_platform.get(r["platform"], 0) + 1
    if by_platform:
        print("  By platform:")
        for p, c in sorted(by_platform.items(), key=lambda x: -x[1]):
            print(f"    {p:<20s} {c}")

    by_source: dict[str, int] = {}
    for r in results:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    if by_source:
        print("  By source:")
        for s, c in sorted(by_source.items(), key=lambda x: -x[1]):
            print(f"    {s:<20s} {c}")
    print(f"{'=' * 78}")

    # Save JSON for review
    out_path = "url_discovery_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved results to {out_path}")

    # ------------------------------------------------------------------
    # Database update
    # ------------------------------------------------------------------
    if results and not args.dry_run:
        print(f"\nUpdating {len(results)} entities in database...")
        updated = save_results_to_db(results)
        print(f"  Updated {updated} rows")
    elif args.dry_run and results:
        print(f"\n[DRY RUN] Would update {len(results)} entities")


if __name__ == "__main__":
    main()
