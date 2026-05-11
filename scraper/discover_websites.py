"""
Discover meeting minutes pages by visiting each organization's website.

For each entity without a known platform, generates candidate website URLs,
visits them, and spiders for links to meeting minutes pages. Detects the
platform from the minutes page (BoardDocs, Legistar, CivicPlus, etc.)
or identifies static HTML sites posting PDF minutes.

Usage:
    python -m discover_websites [--type SCHOOL_DISTRICT] [--limit 100] [--workers 5]
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import httpx

from scraper.db import get_connection, get_cursor

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Keywords that suggest a link points to meeting minutes
MINUTES_KEYWORDS = [
    "meeting minutes", "board minutes", "council minutes", "minutes",
    "meeting agendas", "board agendas", "agendas & minutes", "agendas and minutes",
    "board meetings", "council meetings", "board of education",
    "boarddocs", "board docs", "legistar", "granicus",
    "public meetings", "meeting archive", "meeting calendar",
    "agenda center", "agendacenter",
]

# Keywords in URLs that suggest minutes pages
URL_MINUTES_PATTERNS = [
    "minutes", "agenda", "meeting", "boarddocs", "legistar",
    "granicus", "civicclerk", "agendacenter",
    "board-meetings", "board_meetings", "boardmeeting",
    "council-meetings", "public-meetings",
]

# Platform detection patterns
PLATFORM_PATTERNS = {
    "BOARDDOCS": [
        r"go\.boarddocs\.com",
        r"boarddocs\.com",
    ],
    "GRANICUS": [
        r"[\w]+\.legistar\.com",
        r"webapi\.legistar\.com",
        r"[\w]+\.granicus\.com",
        r"legistar",
    ],
    "CIVICPLUS_AGENDA": [
        r"civicplus\.com",
        r"/agendacenter",
        r"/AgendaCenter",
    ],
    "CIVICCLERK": [
        r"civicclerk\.com",
    ],
    "IQM2": [
        r"iqm2\.com",
    ],
    "CIVICWEB": [
        r"civicweb\.net",
    ],
}


def detect_platform(url: str, body: str = "") -> str | None:
    """Detect the meeting platform from a URL and optional page body."""
    combined = (url + " " + body).lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return platform
    return None


def generate_website_urls(name: str, entity_type: str) -> list[str]:
    """Generate candidate website URLs for an entity."""
    candidates = []

    # Clean name for URL generation
    clean = name.lower().strip()
    clean = re.sub(r"[^a-z0-9\s-]", "", clean)
    words = clean.split()

    # Remove common suffixes
    suffixes_to_strip = [
        "intermediate school district", "community schools", "public schools",
        "area schools", "school district", "schools", "township", "county",
        "charter school", "charter academy", "academy",
    ]
    stripped = clean
    for suffix in suffixes_to_strip:
        if stripped.endswith(suffix):
            stripped = stripped[:-len(suffix)].strip(" -")

    slug = stripped.replace(" ", "")
    slug_hyphen = stripped.replace(" ", "-")
    slug_words = stripped.split()

    if entity_type == "SCHOOL_DISTRICT":
        # School district patterns
        candidates.extend([
            f"https://www.{slug}.org",
            f"https://www.{slug}.k12.mi.us",
            f"https://{slug}.org",
            f"https://www.{slug}schools.org",
            f"https://www.{slug}schools.com",
            f"https://www.{slug_hyphen}.org",
        ])
        if len(slug_words) >= 2:
            # Try first word + "schools"
            candidates.append(f"https://www.{slug_words[0]}schools.org")
            candidates.append(f"https://www.{slug_words[0]}.k12.mi.us")

    elif entity_type == "ISD":
        candidates.extend([
            f"https://www.{slug}.org",
            f"https://www.{slug_hyphen}.org",
            f"https://{slug}.org",
        ])
        # Try common ISD URL patterns
        if slug_words:
            base = slug_words[0]
            candidates.extend([
                f"https://www.{base}isd.org",
                f"https://www.{base}resa.org",
                f"https://www.{base}esd.org",
            ])

    elif entity_type == "TOWNSHIP":
        if slug_words:
            base = slug_words[0]
            candidates.extend([
                f"https://www.{base}township.com",
                f"https://www.{base}twp.com",
                f"https://www.{base}township.org",
                f"https://www.{base}twp.org",
                f"https://www.{slug}township.com",
                f"https://{base}-township.com",
                f"https://www.{base}townshipmi.gov",
                f"https://{base}twp.org",
            ])

    elif entity_type == "CITY":
        if slug_words:
            base = slug_words[0]
            candidates.extend([
                f"https://www.cityof{base}.com",
                f"https://www.cityof{base}.org",
                f"https://www.{base}mi.gov",
                f"https://www.{base}.org",
                f"https://www.ci.{base}.mi.us",
                f"https://cityof{base}.com",
                f"https://www.{base}city.com",
            ])

    elif entity_type == "VILLAGE":
        if slug_words:
            base = slug_words[0]
            candidates.extend([
                f"https://www.villageof{base}.com",
                f"https://www.villageof{base}.org",
                f"https://www.{base}village.com",
                f"https://www.{base}.org",
                f"https://www.{base}mi.gov",
            ])

    elif entity_type == "COUNTY":
        if slug_words:
            base = slug_words[0]
            candidates.extend([
                f"https://www.{base}countymi.gov",
                f"https://www.co.{base}.mi.us",
                f"https://www.{base}county.org",
                f"https://www.{base}countymi.gov",
            ])

    return candidates


def find_minutes_links(html: str, base_url: str) -> list[dict]:
    """Find links that likely point to meeting minutes pages."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    results = []

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        text = link.get_text(strip=True).lower()
        href_lower = href.lower()

        # Skip empty, javascript, mailto, etc.
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        # Make absolute
        abs_url = urljoin(base_url, href)

        # Check if link text or URL matches minutes patterns
        score = 0

        # Text-based scoring
        for keyword in MINUTES_KEYWORDS:
            if keyword in text:
                score += 3
                break

        # URL-based scoring
        for pattern in URL_MINUTES_PATTERNS:
            if pattern in href_lower:
                score += 2
                break

        # Platform detection in URL
        platform = detect_platform(abs_url)
        if platform:
            score += 5

        if score >= 2:
            results.append({
                "url": abs_url,
                "text": link.get_text(strip=True)[:100],
                "score": score,
                "platform": platform,
            })

    # Sort by score descending
    results.sort(key=lambda x: -x["score"])
    return results


def check_website(entity: dict) -> dict | None:
    """Check an entity's candidate websites for meeting minutes pages.

    Returns a dict with discovered minutes URL and platform, or None.
    """
    entity_id = entity["id"]
    entity_name = entity["name"]
    entity_type = entity["type"]

    urls = generate_website_urls(entity_name, entity_type)
    if not urls:
        return None

    client = httpx.Client(
        headers=HEADERS,
        timeout=10,
        follow_redirects=True,
    )

    try:
        for url in urls:
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    continue

                # Check if the homepage itself is a known platform
                final_url = str(resp.url)
                platform = detect_platform(final_url, resp.text[:5000])
                if platform:
                    return {
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "website_url": final_url,
                        "minutes_url": final_url,
                        "platform": platform,
                        "source": "homepage_redirect",
                    }

                # Search for minutes links on the page
                minutes_links = find_minutes_links(resp.text, final_url)
                if minutes_links:
                    best = minutes_links[0]
                    # If the best link is to a known platform, use it directly
                    if best["platform"]:
                        return {
                            "entity_id": entity_id,
                            "entity_name": entity_name,
                            "website_url": final_url,
                            "minutes_url": best["url"],
                            "platform": best["platform"],
                            "source": "link_on_homepage",
                            "link_text": best["text"],
                        }

                    # Follow the link and check the target page
                    try:
                        sub_resp = client.get(best["url"])
                        if sub_resp.status_code == 200:
                            sub_url = str(sub_resp.url)
                            sub_platform = detect_platform(sub_url, sub_resp.text[:5000])

                            if sub_platform:
                                return {
                                    "entity_id": entity_id,
                                    "entity_name": entity_name,
                                    "website_url": final_url,
                                    "minutes_url": sub_url,
                                    "platform": sub_platform,
                                    "source": "followed_link",
                                    "link_text": best["text"],
                                }

                            # Check if the target page has PDF links (static HTML minutes)
                            pdf_count = len(re.findall(r'\.pdf["\s>]', sub_resp.text, re.IGNORECASE))
                            minutes_words = sum(
                                1 for kw in ["minutes", "meeting", "agenda"]
                                if kw in sub_resp.text.lower()
                            )
                            if pdf_count >= 3 and minutes_words >= 2:
                                return {
                                    "entity_id": entity_id,
                                    "entity_name": entity_name,
                                    "website_url": final_url,
                                    "minutes_url": sub_url,
                                    "platform": "STATIC_HTML",
                                    "source": "pdf_page",
                                    "link_text": best["text"],
                                    "pdf_count": pdf_count,
                                }
                    except Exception:
                        pass

                    # Even if we couldn't determine platform, record the website URL
                    # if the link scored high enough
                    if best["score"] >= 4:
                        return {
                            "entity_id": entity_id,
                            "entity_name": entity_name,
                            "website_url": final_url,
                            "minutes_url": best["url"],
                            "platform": "UNKNOWN",
                            "source": "high_score_link",
                            "link_text": best["text"],
                        }

                # If we found the website but no minutes links, still record it
                # (useful for future manual review)
                # Check if there's at least a "board" or "meetings" link
                board_links = find_minutes_links(resp.text, final_url)
                if not board_links:
                    # Website exists but no meeting-related links
                    continue

            except httpx.TimeoutException:
                continue
            except httpx.ConnectError:
                continue
            except Exception:
                continue

    finally:
        client.close()

    return None


def load_entities(entity_type: str | None = None, limit: int = 0) -> list[dict]:
    """Load entities needing discovery."""
    conn = get_connection()
    try:
        with get_cursor(conn) as cur:
            query = """
                SELECT e.id, e.name, e.type::text as type,
                       e.platform::text as platform,
                       e."minutesUrl", e."websiteUrl",
                       c.name as county_name
                FROM "Entity" e
                LEFT JOIN "County" c ON e."countyId" = c.id
                WHERE (e.platform::text = 'UNKNOWN' OR e.platform IS NULL)
                  AND (e."minutesUrl" IS NULL OR e."minutesUrl" = '')
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

    parser = argparse.ArgumentParser(description="Discover meeting minutes by visiting websites")
    parser.add_argument("--type", type=str, default=None, help="Filter by entity type")
    parser.add_argument("--limit", type=int, default=0, help="Max entities to check (0=all)")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent workers")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database")
    args = parser.parse_args()

    entities = load_entities(entity_type=args.type, limit=args.limit)
    print(f"Loaded {len(entities)} entities needing discovery")

    if not entities:
        print("No entities to discover. All have platform/minutesUrl set.")
        return

    # Count by type
    by_type: dict[str, int] = {}
    for e in entities:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c}")

    results: list[dict] = []
    errors = 0
    checked = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_website, e): e for e in entities}
        for future in as_completed(futures):
            checked += 1
            entity = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    print(
                        f"  [{checked}/{len(entities)}] FOUND: {result['entity_name'][:40]:40s} "
                        f"-> {result['platform']:15s} {result['minutes_url'][:60]}"
                    )
                elif checked % 50 == 0:
                    print(f"  [{checked}/{len(entities)}] checked... ({len(results)} found)")
            except Exception as exc:
                errors += 1
                if checked % 50 == 0:
                    print(f"  [{checked}/{len(entities)}] error: {exc}")

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"WEBSITE DISCOVERY RESULTS")
    print(f"{'=' * 70}")
    print(f"  Checked:     {checked}")
    print(f"  Found:       {len(results)}")
    print(f"  Errors:      {errors}")

    by_platform: dict[str, int] = {}
    for r in results:
        by_platform[r["platform"]] = by_platform.get(r["platform"], 0) + 1
    for p, c in sorted(by_platform.items()):
        print(f"    {p}: {c}")
    print(f"{'=' * 70}")

    # Update database
    if results and not args.dry_run:
        print(f"\nUpdating {len(results)} entities in database...")
        conn = get_connection()
        updated = 0
        try:
            with get_cursor(conn) as cur:
                for r in results:
                    platform = r["platform"]
                    if platform == "UNKNOWN":
                        # Don't set platform to UNKNOWN, just set the website/minutes URL
                        cur.execute(
                            """
                            UPDATE "Entity"
                            SET "websiteUrl" = COALESCE("websiteUrl", %s),
                                "minutesUrl" = %s,
                                "updatedAt" = NOW()
                            WHERE id = %s
                            """,
                            (r.get("website_url"), r["minutes_url"], r["entity_id"]),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE "Entity"
                            SET platform = %s,
                                "websiteUrl" = COALESCE("websiteUrl", %s),
                                "minutesUrl" = %s,
                                "scrapeStatus" = 'PENDING',
                                "updatedAt" = NOW()
                            WHERE id = %s
                            """,
                            (platform, r.get("website_url"), r["minutes_url"], r["entity_id"]),
                        )
                    updated += 1
            print(f"  Updated {updated} entities")
        finally:
            conn.close()

    # Save results for review
    with open("website_discovery_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved results to website_discovery_results.json")


if __name__ == "__main__":
    main()
