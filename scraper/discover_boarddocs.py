"""
Discover Michigan BoardDocs organizations by probing URLs.

Generates candidate codes algorithmically from entity names in the database,
then probes go.boarddocs.com/mi/{code}/Board.nsf to find valid BoardDocs sites.

Usage:
    python -m discover_boarddocs [--workers 10] [--type SCHOOL_DISTRICT]
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from scraper.db import get_connection, get_cursor

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

STOP_WORDS = {
    "of", "the", "and", "for", "in", "at", "to", "a", "an", "on", "or",
    "public", "community", "area", "charter", "academy", "district",
}

# Suffixes to strip from entity names before generating codes
NAME_SUFFIXES = [
    "intermediate school district",
    "community school district",
    "public school district",
    "area school district",
    "community schools",
    "public schools",
    "area schools",
    "school district",
    "public school academy",
    "charter school",
    "charter academy",
    "schools",
    "township",
    "county",
    "city of",
    "village of",
    "board of education",
]

# ISD suffix patterns
ISD_SUFFIXES = [
    "intermediate school district",
    "regional education service agency",
    "regional education service district",
    "educational service agency",
    "educational service district",
    "education service district",
]


def strip_name(name: str) -> str:
    """Strip common organizational suffixes from an entity name."""
    lower = name.lower().strip()
    for suffix in NAME_SUFFIXES:
        if lower.endswith(suffix):
            lower = lower[: -len(suffix)].strip(" -,")
    # Also strip leading "city of", "village of", etc.
    for prefix in ["city of ", "village of ", "township of ", "charter township of "]:
        if lower.startswith(prefix):
            lower = lower[len(prefix) :].strip()
    return lower


def generate_candidates(entity_name: str, entity_type: str, county_name: str | None = None) -> list[str]:
    """Generate candidate BoardDocs codes from an entity name.

    Uses patterns observed in the 82 already-discovered Michigan BoardDocs codes:
    - Full name no spaces: annarbor, grandrapids, byroncenter
    - First word only: alma, alpena, caro, clio
    - First 3-5 chars: dur, dec, man, flush
    - Initialism: aaps, csps, mps, pccs
    - Initialism + suffix (ps, sd, cs): troysd, mhsd, slps
    - First two words combined: byroncenter, huronvalley
    - ISD patterns: genisd, diisd, washisd, maisd
    - County patterns: midco, jackson
    """
    candidates: set[str] = set()

    # Clean the name
    clean = strip_name(entity_name)
    words = [w for w in clean.split() if w]
    if not words:
        return []

    # Also get significant words (excluding stop words)
    sig_words = [w for w in words if w not in STOP_WORDS]
    if not sig_words:
        sig_words = words

    # --- Strategy 1: Full cleaned name, no spaces ---
    full = "".join(words)
    candidates.add(full)
    if len(full) <= 15:
        candidates.add(full)

    # --- Strategy 2: First significant word ---
    first = sig_words[0]
    candidates.add(first)

    # --- Strategy 3: First 3, 4, 5 chars of first significant word ---
    for n in [3, 4, 5, 6]:
        if len(first) >= n:
            candidates.add(first[:n])

    # --- Strategy 4: Initialism of significant words ---
    if len(sig_words) >= 2:
        initials = "".join(w[0] for w in sig_words)
        candidates.add(initials)

        # Initials + common suffixes
        for suffix in ["ps", "sd", "cs", "as", "s", "psd", "csd"]:
            candidates.add(initials + suffix)

    # --- Strategy 5: First two words combined ---
    if len(words) >= 2:
        candidates.add(words[0] + words[1])
        # Also try first sig words
        if len(sig_words) >= 2:
            candidates.add(sig_words[0] + sig_words[1])

    # --- Strategy 6: Type-specific patterns ---
    if entity_type == "ISD":
        # ISD naming: countyisd, countyresa, countyesd, etc.
        base = sig_words[0] if sig_words else words[0]
        for suffix in ["isd", "resa", "resd", "esd", "esa"]:
            candidates.add(base + suffix)
            if len(base) >= 3:
                candidates.add(base[:3] + suffix)
            if len(base) >= 4:
                candidates.add(base[:4] + suffix)
        # Multi-word ISD names (e.g., "Bay-Arenac" -> "bayisd", "baisd")
        if "-" in entity_name.lower() or len(sig_words) >= 2:
            combined_initials = "".join(w[0] for w in sig_words[:3])
            for suffix in ["isd", "resa", "esd"]:
                candidates.add(combined_initials + suffix)

    elif entity_type == "COUNTY":
        base = sig_words[0] if sig_words else words[0]
        candidates.add(base + "co")
        candidates.add(base + "county")
        if len(base) >= 3:
            candidates.add(base[:3] + "co")
        # Also try the county name directly
        if county_name:
            cn = county_name.lower().strip()
            candidates.add(cn)
            candidates.add(cn + "co")

    elif entity_type in ("SCHOOL_DISTRICT", "CHARTER_SCHOOL"):
        base = sig_words[0] if sig_words else words[0]
        for suffix in ["sd", "ps", "cs", "psd", "csd"]:
            candidates.add(base + suffix)
        # Also the full original name words (e.g., "Plymouth-Canton" -> "plymouthcanton")
        orig_words = re.sub(r"[^a-z0-9\s]", "", entity_name.lower()).split()
        orig_sig = [w for w in orig_words if w not in STOP_WORDS and w not in NAME_SUFFIXES]
        if len(orig_sig) >= 2:
            candidates.add(orig_sig[0] + orig_sig[1])

    elif entity_type in ("CITY", "VILLAGE"):
        base = sig_words[0] if sig_words else words[0]
        candidates.add(base)
        candidates.add(base + "mi")
        candidates.add("cityof" + base)

    elif entity_type == "TOWNSHIP":
        base = sig_words[0] if sig_words else words[0]
        candidates.add(base)
        candidates.add(base + "twp")
        candidates.add(base + "township")

    # Filter: only codes 2-20 chars, alphanumeric
    return sorted(
        c for c in candidates
        if 2 <= len(c) <= 20 and c.isalnum()
    )


def check_code(code: str) -> dict | None:
    """Test a BoardDocs code. Returns info dict if valid, None if not."""
    url = f"https://go.boarddocs.com/mi/{code}/Board.nsf/Public"
    try:
        r = httpx.get(url, timeout=12, follow_redirects=True, headers=HEADERS)
        if r.status_code == 200 and "BoardDocs" in r.text:
            title = ""
            if "<title>" in r.text:
                start = r.text.index("<title>") + 7
                end = r.text.index("</title>", start)
                title = r.text[start:end].strip()
                for suffix in [
                    "BoardDocs\u00ae LT Plus",
                    "BoardDocs\u00ae LT",
                    "BoardDocs\u00ae PL",
                    "BoardDocs\u00ae Pro",
                    "BoardDocs\u00ae Plus",
                    "BoardDocs",
                ]:
                    title = title.replace(suffix, "").strip()
                title = title.strip(" -|")
            return {"code": code, "title": title, "url": url}
    except Exception:
        pass
    return None


def load_entities(entity_type: str | None = None) -> list[dict]:
    """Load entities from the database."""
    conn = get_connection()
    try:
        with get_cursor(conn) as cur:
            query = """
                SELECT e.id, e.name, e.type::text as type, e.platform::text as platform,
                       e."platformCode", e."minutesUrl",
                       c.name as county_name
                FROM "Entity" e
                LEFT JOIN "County" c ON e."countyId" = c.id
            """
            conditions = []
            params = []
            if entity_type:
                conditions.append("e.type::text = %s")
                params.append(entity_type)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY e.name"

            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Discover BoardDocs organizations")
    parser.add_argument("--workers", type=int, default=10, help="Concurrent workers")
    parser.add_argument("--type", type=str, default=None, help="Filter by entity type")
    parser.add_argument("--only-unknown", action="store_true", help="Only check entities with platform=UNKNOWN")
    args = parser.parse_args()

    # Load entities from database
    entities = load_entities(entity_type=args.type)
    print(f"Loaded {len(entities)} entities from database")

    if args.only_unknown:
        entities = [e for e in entities if (e.get("platform") or "UNKNOWN") == "UNKNOWN"]
        print(f"  {len(entities)} with platform=UNKNOWN")

    # Generate candidate codes for each entity
    code_to_entities: dict[str, list[dict]] = {}
    for entity in entities:
        # Skip entities already on BoardDocs
        if entity.get("platform") == "BOARDDOCS" and entity.get("platformCode"):
            continue

        candidates = generate_candidates(
            entity["name"],
            entity["type"],
            entity.get("county_name"),
        )
        for code in candidates:
            if code not in code_to_entities:
                code_to_entities[code] = []
            code_to_entities[code].append(entity)

    # Load previously discovered codes to skip
    existing_codes: set[str] = set()
    try:
        with open("boarddocs_discovered.json") as f:
            for item in json.load(f):
                existing_codes.add(item["code"].lower())
    except FileNotFoundError:
        pass

    # Filter out already-discovered codes
    new_codes = {c: e for c, e in code_to_entities.items() if c.lower() not in existing_codes}
    print(f"Generated {len(code_to_entities)} unique candidate codes")
    print(f"  {len(existing_codes)} already discovered, {len(new_codes)} new to probe")

    # Also re-probe existing codes to get fresh data
    codes_to_probe = list(new_codes.keys()) + list(existing_codes)
    total = len(codes_to_probe)
    print(f"Probing {total} codes ({len(new_codes)} new + {len(existing_codes)} existing)...")

    found: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_code, code): code for code in codes_to_probe}
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
                print(f"  [{done}/{total}] FOUND: {code:20s} -> {result['title'][:60]}")
            elif done % 100 == 0:
                print(f"  [{done}/{total}] checked... ({len(found)} found so far)")

    found.sort(key=lambda x: x["code"])

    # Save results
    with open("boarddocs_discovered.json", "w") as fp:
        json.dump(found, fp, indent=2)

    print(f"\n{'=' * 60}")
    print(f"RESULTS: Found {len(found)} BoardDocs organizations in Michigan")
    print(f"  New discoveries: {len(found) - len(existing_codes.intersection(f['code'].lower() for f in found))}")
    print(f"{'=' * 60}")

    for f in found:
        entities_str = ""
        if f.get("candidate_entities"):
            entities_str = f" <- {f['candidate_entities'][0]['name']}"
        print(f"  {f['code']:20s} {f['title'][:50]}{entities_str}")

    print(f"\nSaved to boarddocs_discovered.json")


if __name__ == "__main__":
    main()
