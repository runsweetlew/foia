"""
Discover Michigan municipalities using the Legistar platform.

Probes the Legistar REST API (webapi.legistar.com) with candidate client
codes generated from entity names. The API is free and unauthenticated.

Usage:
    python -m discover_legistar [--workers 5] [--limit 100]
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from scraper.db import get_connection, get_cursor

LEGISTAR_API = "https://webapi.legistar.com/v1"


def generate_legistar_codes(name: str, entity_type: str) -> list[str]:
    """Generate candidate Legistar client codes from an entity name.

    Legistar client codes are typically the municipality name, sometimes
    with state suffix. Examples: annarbor, detroit, grandrapids, lansingmi.
    """
    candidates: set[str] = set()

    clean = name.lower().strip()
    # Strip suffixes
    for suffix in [
        "intermediate school district", "community schools", "public schools",
        "area schools", "school district", "schools", "township", "county",
        "charter school", "charter academy", "board of education",
    ]:
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)].strip(" -,")
    for prefix in ["city of ", "village of ", "township of ", "charter township of "]:
        if clean.startswith(prefix):
            clean = clean[len(prefix):]

    clean = re.sub(r"[^a-z0-9\s]", "", clean).strip()
    words = clean.split()
    if not words:
        return []

    # Full name no spaces
    full = "".join(words)
    candidates.add(full)

    # First word
    candidates.add(words[0])

    # Full + "mi" suffix
    candidates.add(full + "mi")
    candidates.add(words[0] + "mi")

    # Hyphenated
    if len(words) >= 2:
        candidates.add(words[0] + words[1])

    # County-specific patterns
    if entity_type == "COUNTY":
        candidates.add(words[0] + "county")
        candidates.add(words[0] + "countyboardofcommissioners")

    return sorted(c for c in candidates if 3 <= len(c) <= 30)


def _is_michigan_client(code: str) -> bool:
    """Check if a Legistar client is in Michigan by inspecting the web page."""
    try:
        r = httpx.get(
            f"https://{code}.legistar.com/Calendar.aspx",
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if r.status_code == 200:
            body = r.text.lower()
            # Check for Michigan references in the page
            return any(kw in body for kw in [
                "michigan", ", mi ", ", mi.", "mi 4", "mi 3",  # MI zip codes start with 4 or 3
            ])
    except Exception:
        pass
    return False


def check_legistar_code(code: str) -> dict | None:
    """Test if a Legistar client code is valid and in Michigan."""
    url = f"{LEGISTAR_API}/{code}/events?$top=1"
    try:
        r = httpx.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                # Valid client with events — verify it's in Michigan
                if not _is_michigan_client(code):
                    return None
                event = data[0]
                body_name = event.get("EventBodyName", "")
                return {
                    "code": code,
                    "url": f"https://{code}.legistar.com/Calendar.aspx",
                    "api_url": f"{LEGISTAR_API}/{code}/events",
                    "sample_body": body_name,
                    "has_events": True,
                }
            elif isinstance(data, list) and len(data) == 0:
                # Valid client but no events — verify Michigan
                if not _is_michigan_client(code):
                    return None
                return {
                    "code": code,
                    "url": f"https://{code}.legistar.com/Calendar.aspx",
                    "api_url": f"{LEGISTAR_API}/{code}/events",
                    "sample_body": "",
                    "has_events": False,
                }
    except Exception:
        pass
    return None


def load_entities(limit: int = 0) -> list[dict]:
    """Load entities that might use Legistar (cities, counties, larger entities)."""
    conn = get_connection()
    try:
        with get_cursor(conn) as cur:
            query = """
                SELECT e.id, e.name, e.type::text as type,
                       e.platform::text as platform,
                       c.name as county_name
                FROM "Entity" e
                LEFT JOIN "County" c ON e."countyId" = c.id
                WHERE (e.platform::text = 'UNKNOWN' OR e.platform IS NULL)
                  AND e.type::text IN ('CITY', 'COUNTY', 'VILLAGE', 'TOWNSHIP', 'SCHOOL_DISTRICT', 'ISD')
                ORDER BY
                    CASE e.type::text
                        WHEN 'CITY' THEN 1
                        WHEN 'COUNTY' THEN 2
                        WHEN 'VILLAGE' THEN 3
                        WHEN 'TOWNSHIP' THEN 4
                        WHEN 'SCHOOL_DISTRICT' THEN 5
                        WHEN 'ISD' THEN 6
                    END,
                    e.name
            """
            params: list = []
            if limit > 0:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Discover Legistar clients in Michigan")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent workers")
    parser.add_argument("--limit", type=int, default=0, help="Max entities to check")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database")
    args = parser.parse_args()

    entities = load_entities(limit=args.limit)
    print(f"Loaded {len(entities)} candidate entities")

    # Generate codes
    code_to_entities: dict[str, list[dict]] = {}
    for entity in entities:
        codes = generate_legistar_codes(entity["name"], entity["type"])
        for code in codes:
            if code not in code_to_entities:
                code_to_entities[code] = []
            code_to_entities[code].append(entity)

    codes = list(code_to_entities.keys())
    total = len(codes)
    print(f"Generated {total} unique candidate codes to probe")

    found: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_legistar_code, code): code for code in codes}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result:
                code = result["code"]
                result["candidate_entities"] = [
                    {"id": e["id"], "name": e["name"], "type": e["type"]}
                    for e in code_to_entities.get(code, [])
                ]
                found.append(result)
                entities_str = ""
                if result["candidate_entities"]:
                    entities_str = f" <- {result['candidate_entities'][0]['name']}"
                print(f"  [{done}/{total}] FOUND: {code:25s} body={result['sample_body'][:40]}{entities_str}")
            elif done % 100 == 0:
                print(f"  [{done}/{total}] checked... ({len(found)} found)")

    print(f"\n{'=' * 60}")
    print(f"Found {len(found)} Legistar clients in Michigan")
    print(f"  With events: {sum(1 for f in found if f['has_events'])}")
    print(f"  Empty:       {sum(1 for f in found if not f['has_events'])}")
    print(f"{'=' * 60}")

    # Save results
    with open("legistar_discovered.json", "w") as f:
        json.dump(found, f, indent=2)
    print(f"Saved to legistar_discovered.json")

    # Match to entities and update database
    if found and not args.dry_run:
        print(f"\nUpdating matched entities in database...")
        conn = get_connection()
        updated = 0
        try:
            with get_cursor(conn) as cur:
                for item in found:
                    if not item.get("has_events"):
                        continue
                    for ce in item.get("candidate_entities", []):
                        minutes_url = item["url"]
                        cur.execute(
                            """
                            UPDATE "Entity"
                            SET platform = 'GRANICUS',
                                "minutesUrl" = %s,
                                "platformCode" = %s,
                                "scrapeStatus" = 'PENDING',
                                "updatedAt" = NOW()
                            WHERE id = %s
                              AND (platform::text = 'UNKNOWN' OR platform IS NULL
                                   OR "minutesUrl" IS NULL OR "minutesUrl" = '')
                            """,
                            (minutes_url, item["code"], ce["id"]),
                        )
                        if cur.rowcount > 0:
                            updated += 1
                            print(f"  Updated: {ce['name']} -> {item['code']}")
            print(f"\n  Total updated: {updated}")
        finally:
            conn.close()
    elif args.dry_run and found:
        print(f"\n[DRY RUN] Would update entities for {len(found)} Legistar clients")


if __name__ == "__main__":
    main()
