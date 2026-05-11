"""
Discover meeting minutes pages using Google search.

For entities with no minutesUrl, searches Google for their meeting minutes
page and updates the database with the result.

Uses the googlesearch-python package (no API key needed).

Usage:
    python -m discover_google [--type TOWNSHIP] [--limit 100] [--delay 5]
"""
from __future__ import annotations

import re
import time
from urllib.parse import urlparse

import httpx
import structlog

from scraper.db import get_connection, get_cursor

log = structlog.get_logger()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36",
}

# Platform detection from URLs
PLATFORM_URL_PATTERNS = {
    "BOARDDOCS": [r"boarddocs\.com"],
    "GRANICUS": [r"legistar\.com", r"granicus\.com"],
    "CIVICPLUS_AGENDA": [r"/agendacenter", r"/AgendaCenter", r"civicplus\.com"],
    "CIVICCLERK": [r"civicclerk\.com"],
    "IQM2": [r"iqm2\.com"],
    "CIVICWEB": [r"civicweb\.net"],
    "PRIMEGOV": [r"primegov\.com"],
}

# Domains to skip (not useful results)
SKIP_DOMAINS = {
    "facebook.com", "twitter.com", "x.com", "linkedin.com",
    "youtube.com", "instagram.com", "yelp.com", "yellowpages.com",
    "mapquest.com", "google.com", "wikipedia.org", "zillow.com",
    "trulia.com", "realtor.com", "indeed.com", "glassdoor.com",
    "amazon.com", "pinterest.com", "tiktok.com",
    # News sites that often mention meeting minutes
    "cbsnews.com", "nbcnews.com", "cnn.com", "foxnews.com",
    "timesofisrael.com", "reuters.com", "apnews.com",
    "mlive.com", "detroitnews.com", "freep.com",
    "bridgemi.com", "michiganradio.org",
    "patch.com", "hometownlife.com",
    # Other non-government sites
    "baymetro.com", "meetup.com", "eventbrite.com",
    "citizenportal.ai", "ballotpedia.org",
    "mml.org", "michigan.gov",
}


def detect_platform_from_url(url: str) -> str | None:
    """Detect platform from a URL string."""
    url_lower = url.lower()
    for platform, patterns in PLATFORM_URL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return platform
    return None


def build_search_query(entity: dict) -> str:
    """Build a Google search query for an entity's meeting minutes."""
    name = entity["name"]
    entity_type = entity["type"]

    # Entity names already include type suffix (e.g. "Alcona County", "Ada Township")
    if entity_type == "SCHOOL_DISTRICT":
        return f'"{name}" michigan school board meeting minutes'
    elif entity_type == "ISD":
        return f'"{name}" michigan board meeting minutes'
    else:
        return f'"{name}" michigan meeting minutes'


def web_search(query: str, num_results: int = 5) -> list[str]:
    """Perform a web search and return result URLs.

    Uses the ddgs package (DuckDuckGo) as primary, with fallbacks.
    """
    # Primary: ddgs package (handles rate limits, proxies, etc.)
    try:
        from ddgs import DDGS
        results = DDGS().text(query, max_results=num_results)
        urls = [r["href"] for r in results if r.get("href")]
        if urls:
            return urls
    except Exception as e:
        log.debug("web_search.ddgs_error", error=str(e))

    # Fallback: raw DDG HTML scraping
    urls = duckduckgo_search(query, num_results)
    if urls:
        return urls

    # Last resort: googlesearch-python
    try:
        from googlesearch import search
        return list(search(query, num_results=num_results, lang="en"))
    except Exception:
        pass

    return []


def duckduckgo_search(query: str, num_results: int = 5) -> list[str]:
    """Search using DuckDuckGo HTML (no API key needed)."""
    import urllib.parse

    urls = []
    try:
        # Use a simple User-Agent — DDG returns 202 with complex UA strings
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.select("a.result__a"):
                href = link.get("href", "")
                # DDG wraps URLs in redirect links like //duckduckgo.com/l/?uddg=...
                if "uddg=" in href:
                    # Normalize protocol-relative URLs
                    if href.startswith("//"):
                        href = "https:" + href
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if "uddg" in parsed:
                        href = parsed["uddg"][0]
                if href.startswith("http"):
                    urls.append(href)
                    if len(urls) >= num_results:
                        break
    except Exception as e:
        log.warning("duckduckgo_search.error", query=query, error=str(e))
    return urls


def check_url_for_minutes(url: str) -> dict | None:
    """Verify a URL has meeting minutes content and detect its platform."""
    platform = detect_platform_from_url(url)
    if platform:
        return {"url": url, "platform": platform, "source": "url_pattern"}

    # Visit the page and check for minutes content
    try:
        client = httpx.Client(headers=HEADERS, timeout=10, follow_redirects=True)
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                return None

            final_url = str(resp.url)
            body = resp.text.lower()

            # Check redirected URL for platform
            platform = detect_platform_from_url(final_url)
            if platform:
                return {"url": final_url, "platform": platform, "source": "redirect"}

            # Check body for platform markers
            if "boarddocs" in body:
                return {"url": final_url, "platform": "BOARDDOCS", "source": "body"}
            if "granicus" in body or "legistar" in body:
                return {"url": final_url, "platform": "GRANICUS", "source": "body"}
            if "civicclerk" in body:
                return {"url": final_url, "platform": "CIVICCLERK", "source": "body"}

            # Check for static HTML with PDF links
            pdf_count = len(re.findall(r'\.pdf["\s>\'?]', body))
            minutes_words = sum(
                1 for kw in ["minutes", "meeting", "agenda", "board"]
                if kw in body
            )
            if pdf_count >= 3 and minutes_words >= 2:
                return {"url": final_url, "platform": "STATIC_HTML", "source": "pdf_heuristic"}

        finally:
            client.close()
    except Exception:
        pass

    return None


def _url_matches_entity(url: str, entity: dict) -> bool:
    """Check if a URL plausibly belongs to the given entity.

    Prevents false positives where a search for "Bohemia Township" returns
    the Washtenaw County board minutes page instead.
    """
    name = entity["name"].lower()
    entity_type = entity.get("type", "")
    domain = urlparse(url).netloc.lower().replace("www.", "")
    path = urlparse(url).path.lower()
    full = (domain + path).replace("-", "").replace("_", "")

    # Strip common suffixes from entity name for matching
    suffixes_to_strip = [
        " public schools", " community schools", " area schools",
        " school district", " community school district",
        " public school district", " area school district",
        " charter school", " charter academy", " schools",
        " township", " county", " village",
    ]
    stripped_name = name
    for suffix in suffixes_to_strip:
        if stripped_name.endswith(suffix):
            stripped_name = stripped_name[: -len(suffix)]
            break

    name_parts = stripped_name.split()
    # Filter out very common words that cause false matches
    common_words = {
        "the", "of", "and", "for", "in", "at", "to", "a", "an",
        "public", "community", "area", "charter", "school", "district",
        "board", "city", "village", "township", "county",
        "east", "west", "north", "south", "central", "upper", "lower",
        "lake", "river", "bay", "port", "mount", "grand", "new",
    }

    # Build checks from meaningful parts of the name
    meaningful_parts = [p for p in name_parts if p not in common_words]
    if not meaningful_parts:
        meaningful_parts = name_parts  # fallback to all parts if all are common

    checks = []
    # Full stripped name, no spaces
    full_name = stripped_name.replace(" ", "")
    if len(full_name) >= 4:
        checks.append(full_name)

    # First meaningful word (must be at least 5 chars to avoid false matches)
    if meaningful_parts:
        first = meaningful_parts[0]
        if len(first) >= 5:
            checks.append(first)

    # First two meaningful words combined
    if len(meaningful_parts) >= 2:
        combined = meaningful_parts[0] + meaningful_parts[1]
        if len(combined) >= 6:
            checks.append(combined)

    # For CivicClerk portals, check the subdomain pattern (e.g., "ioniami")
    if "civicclerk.com" in domain:
        subdomain = domain.split(".")[0]
        if meaningful_parts:
            for part in meaningful_parts:
                if len(part) >= 4 and part in subdomain:
                    return True
        # Also check with "mi" suffix
        for part in meaningful_parts:
            if len(part) >= 3 and (part + "mi") == subdomain:
                return True

    for check in checks:
        if check and len(check) >= 4 and check in full:
            return True

    return False


def discover_entity(entity: dict, delay: float = 3.0) -> dict | None:
    """Search for an entity's meeting minutes page."""
    query = build_search_query(entity)

    time.sleep(delay)  # Rate limit

    urls = web_search(query, num_results=5)
    if not urls:
        return None

    for url in urls:
        # Skip social media and other non-useful domains
        domain = urlparse(url).netloc.lower().replace("www.", "")
        if any(skip in domain for skip in SKIP_DOMAINS):
            continue

        # Validate URL relates to this entity (not a random other municipality)
        if not _url_matches_entity(url, entity):
            continue

        result = check_url_for_minutes(url)
        if result and result["platform"] != "UNKNOWN":
            return {
                "entity_id": entity["id"],
                "entity_name": entity["name"],
                "entity_type": entity["type"],
                "minutes_url": result["url"],
                "platform": result["platform"],
                "source": result["source"],
                "search_query": query,
            }

    return None


def load_entities(entity_type: str | None = None, limit: int = 0) -> list[dict]:
    """Load entities needing discovery (no minutesUrl)."""
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


def main():
    import argparse
    import json

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(0),
        processors=[
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )

    parser = argparse.ArgumentParser(description="Discover minutes pages via Google search")
    parser.add_argument("--type", type=str, default=None, help="Filter by entity type")
    parser.add_argument("--limit", type=int, default=0, help="Max entities (0=all)")
    parser.add_argument("--delay", type=float, default=5.0, help="Seconds between searches")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database")
    args = parser.parse_args()

    entities = load_entities(entity_type=args.type, limit=args.limit)
    print(f"Loaded {len(entities)} entities needing discovery")

    if not entities:
        print("No entities to discover.")
        return

    by_type: dict[str, int] = {}
    for e in entities:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c}")

    results: list[dict] = []
    skipped = 0

    for i, entity in enumerate(entities):
        try:
            result = discover_entity(entity, delay=args.delay)
            if result:
                results.append(result)
                print(
                    f"  [{i+1}/{len(entities)}] FOUND: {result['entity_name'][:40]:40s} "
                    f"-> {result['platform']:15s} {result['minutes_url'][:60]}"
                )
            else:
                skipped += 1
                if (i + 1) % 20 == 0:
                    print(f"  [{i+1}/{len(entities)}] checked... ({len(results)} found, {skipped} skipped)")
        except Exception as e:
            print(f"  [{i+1}/{len(entities)}] ERROR: {entity['name']}: {e}")

    print(f"\n{'=' * 70}")
    print(f"GOOGLE DISCOVERY RESULTS")
    print(f"{'=' * 70}")
    print(f"  Checked:  {len(entities)}")
    print(f"  Found:    {len(results)}")
    print(f"  Skipped:  {skipped}")

    by_platform: dict[str, int] = {}
    for r in results:
        by_platform[r["platform"]] = by_platform.get(r["platform"], 0) + 1
    for p, c in sorted(by_platform.items()):
        print(f"    {p}: {c}")
    print(f"{'=' * 70}")

    # Save results
    with open("google_discovery_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved to google_discovery_results.json")

    # Update database
    if results and not args.dry_run:
        print(f"\nUpdating {len(results)} entities in database...")
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
            print(f"  Updated {updated} entities")
        finally:
            conn.close()
    elif args.dry_run:
        print(f"\n[DRY RUN] Would update {len(results)} entities")


if __name__ == "__main__":
    main()
