"""
Match discovered BoardDocs codes to Entity records in the database.

Reads boarddocs_discovered.json, fuzzy-matches each code's title against
entity names, and updates matched entities with platform=BOARDDOCS,
minutesUrl, and platformCode.

Usage:
    python -m match_boarddocs [--dry-run] [--verbose]
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher

from scraper.db import get_connection, get_cursor


# Suffixes to strip when comparing names
STRIP_SUFFIXES = [
    "intermediate school district",
    "regional education service agency",
    "regional education service district",
    "educational service agency",
    "educational service district",
    "education service district",
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
    "board of education",
    "board policies and guidelines",
    "board policies and bylaws",
    "board policy and guidelines",
    "board policy and bylaws",
    "school board policies and guidelines",
    "school board policies and bylaws",
    "school board policies",
    "school board policy",
    "school board agendas and policies",
    "board policy",
    "district policies and administrative guidelines",
]


def normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    s = name.lower().strip()
    # Remove address/phone info (common in BoardDocs titles)
    # Pattern: everything after a pipe, or after a number followed by a street word
    s = re.split(r'\s*\|\s*', s)[0]
    # Remove anything that looks like an address (number + street)
    s = re.sub(r'\d+\s+(w\.?|e\.?|s\.?|n\.?|west|east|south|north)?\s*\w+\s+(street|st|road|rd|avenue|ave|blvd|drive|dr)\b.*', '', s, flags=re.IGNORECASE)
    # Remove phone/fax patterns
    s = re.sub(r'(ph|phone|fax|f|p):\s*[\d\(\)\-\.\s]+', '', s)
    s = re.sub(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}', '', s)
    # Strip known suffixes
    for suffix in STRIP_SUFFIXES:
        if s.endswith(suffix):
            s = s[:-len(suffix)].strip(" -,")
    # Remove "city of", "village of" etc.
    for prefix in ["city of ", "village of ", "township of ", "charter township of ", "county of "]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    # Remove punctuation and extra whitespace
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def match_score(boarddocs_title: str, entity_name: str, raw_title: str = "", entity_type: str = "") -> float:
    """Score how well a BoardDocs title matches an entity name. Returns 0.0-1.0."""
    bt = normalize_name(boarddocs_title)
    en = normalize_name(entity_name)

    # Generic words that shouldn't match anything meaningful
    GENERIC_WORDS = {"school", "board", "district", "policy", "policies", "county",
                     "township", "city", "village", "public", "community", "area"}

    if not bt or not en or bt in GENERIC_WORDS:
        return 0.0

    score = 0.0

    # Exact match after normalization
    if bt == en:
        score = 1.0
    else:
        # Check word-boundary containment (not substring within a word)
        import re as _re
        bt_words = set(bt.split())
        en_words = set(en.split())

        # Check if one full string appears as whole words in the other
        if len(bt) >= 4 and len(en) >= 4:
            # Use word boundary check: "elk rapids" in "elk rapids schools" = yes
            # "school" in "schoolcraft" = no (not a word boundary)
            shorter_s, longer_s = (bt, en) if len(bt) <= len(en) else (en, bt)
            pattern = r'(?:^|\s)' + _re.escape(shorter_s) + r'(?:\s|$)'
            if _re.search(pattern, longer_s):
                score = 0.9

        # Check if all words of the shorter set are in the longer set
        if score < 0.85 and bt_words and en_words:
            overlap = bt_words & en_words
            shorter_len = min(len(bt_words), len(en_words))
            if shorter_len > 0 and len(overlap) / shorter_len >= 0.8:
                score = 0.85

        # Fallback to sequence matcher
        if score < 0.6:
            score = SequenceMatcher(None, bt, en).ratio()

    # BoardDocs is overwhelmingly used by school districts/ISDs.
    # If the raw title contains school-related keywords, prefer SCHOOL_DISTRICT/ISD.
    if raw_title and score >= 0.9:
        raw_lower = raw_title.lower()
        is_school_title = any(kw in raw_lower for kw in ["school", "district", "isd", "resa", "esd", "academy"])
        if is_school_title and entity_type in ("SCHOOL_DISTRICT", "ISD"):
            score += 0.05  # Prefer school entities for school titles
        elif is_school_title and entity_type not in ("SCHOOL_DISTRICT", "ISD"):
            score -= 0.05  # Penalize non-school entities for school titles

    return min(score, 1.0)


def load_entities() -> list[dict]:
    """Load all entities from the database."""
    conn = get_connection()
    try:
        with get_cursor(conn) as cur:
            cur.execute("""
                SELECT e.id, e.name, e.type::text as type, e.platform::text as platform,
                       e."platformCode", e."minutesUrl", e.slug,
                       c.name as county_name
                FROM "Entity" e
                LEFT JOIN "County" c ON e."countyId" = c.id
                ORDER BY e.name
            """)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Match BoardDocs codes to entities")
    parser.add_argument("--dry-run", action="store_true", help="Don't update the database")
    parser.add_argument("--verbose", action="store_true", help="Show all match attempts")
    parser.add_argument("--threshold", type=float, default=0.6, help="Minimum match score (0-1)")
    args = parser.parse_args()

    # Load discovered BoardDocs codes
    try:
        with open("boarddocs_discovered.json") as f:
            discovered = json.load(f)
    except FileNotFoundError:
        print("ERROR: boarddocs_discovered.json not found. Run discover_boarddocs.py first.")
        sys.exit(1)

    print(f"Loaded {len(discovered)} discovered BoardDocs codes")

    # Load entities
    entities = load_entities()
    print(f"Loaded {len(entities)} entities from database")

    # Build lookup by normalized name
    entities_by_norm: dict[str, list[dict]] = {}
    for entity in entities:
        norm = normalize_name(entity["name"])
        if norm not in entities_by_norm:
            entities_by_norm[norm] = []
        entities_by_norm[norm].append(entity)

    matches: list[dict] = []
    unmatched: list[dict] = []
    already_set: list[dict] = []

    for item in discovered:
        code = item["code"]
        title = item["title"]

        # Check if any entity already has this code
        existing = [e for e in entities if e.get("platformCode") == code]
        if existing:
            already_set.append({"code": code, "title": title, "entity": existing[0]["name"]})
            continue

        # Try candidate_entities first (from discovery script)
        best_match = None
        best_score = 0.0

        if item.get("candidate_entities"):
            for ce in item["candidate_entities"]:
                # Find the full entity record
                for entity in entities:
                    if entity["id"] == ce["id"]:
                        score = match_score(title, entity["name"], raw_title=title, entity_type=entity["type"])
                        if score > best_score:
                            best_score = score
                            best_match = entity
                        break

        # Also try matching title against all entities
        if best_score < 0.9:
            for entity in entities:
                score = match_score(title, entity["name"], raw_title=title, entity_type=entity["type"])
                if score > best_score:
                    best_score = score
                    best_match = entity

        # If title is empty/generic, try matching code against entity names
        if best_score < args.threshold and (not title or len(title) < 5 or title.startswith("Board") or title.startswith("School Board") or title.startswith("District")):
            code_lower = code.lower()
            for entity in entities:
                en = normalize_name(entity["name"])
                en_words = en.split()
                # Check if code matches the first word or a common abbreviation
                if en_words and (en_words[0] == code_lower or en_words[0].startswith(code_lower)):
                    score = 0.65
                    if score > best_score:
                        best_score = score
                        best_match = entity

        if best_match and best_score >= args.threshold:
            # Skip if entity is already set to BOARDDOCS with a different code
            if best_match.get("platform") == "BOARDDOCS" and best_match.get("platformCode") and best_match["platformCode"] != code:
                if args.verbose:
                    print(f"  SKIP {code}: {best_match['name']} already has code={best_match['platformCode']}")
                continue

            matches.append({
                "code": code,
                "title": title,
                "entity_id": best_match["id"],
                "entity_name": best_match["name"],
                "entity_type": best_match["type"],
                "score": best_score,
            })
        else:
            unmatched.append({
                "code": code,
                "title": title,
                "best_entity": best_match["name"] if best_match else None,
                "best_score": best_score,
            })

    # Print results
    print(f"\n{'=' * 70}")
    print(f"MATCHING RESULTS")
    print(f"{'=' * 70}")
    print(f"  Already assigned:  {len(already_set)}")
    print(f"  New matches:       {len(matches)}")
    print(f"  Unmatched:         {len(unmatched)}")
    print(f"{'=' * 70}")

    if already_set:
        print(f"\nAlready assigned ({len(already_set)}):")
        for m in already_set:
            print(f"  {m['code']:20s} -> {m['entity']}")

    if matches:
        print(f"\nNew matches ({len(matches)}):")
        for m in sorted(matches, key=lambda x: -x["score"]):
            print(f"  {m['code']:20s} -> {m['entity_name']:40s} (score={m['score']:.2f}, type={m['entity_type']})")

    if unmatched and args.verbose:
        print(f"\nUnmatched ({len(unmatched)}):")
        for m in unmatched:
            best = f" (closest: {m['best_entity']}, score={m['best_score']:.2f})" if m["best_entity"] else ""
            print(f"  {m['code']:20s} title={m['title'][:50]}{best}")

    # Update database
    if matches and not args.dry_run:
        print(f"\nUpdating {len(matches)} entities in database...")
        conn = get_connection()
        updated = 0
        try:
            with get_cursor(conn) as cur:
                for m in matches:
                    minutes_url = f"https://go.boarddocs.com/mi/{m['code']}/Board.nsf/Public"
                    cur.execute(
                        """
                        UPDATE "Entity"
                        SET platform = 'BOARDDOCS',
                            "minutesUrl" = %s,
                            "platformCode" = %s,
                            "scrapeStatus" = 'PENDING',
                            "updatedAt" = NOW()
                        WHERE id = %s
                        """,
                        (minutes_url, m["code"], m["entity_id"]),
                    )
                    updated += 1
            print(f"  Updated {updated} entities")
        finally:
            conn.close()
    elif args.dry_run and matches:
        print(f"\n[DRY RUN] Would update {len(matches)} entities")

    # Save unmatched for manual review
    if unmatched:
        with open("boarddocs_unmatched.json", "w") as f:
            json.dump(unmatched, f, indent=2)
        print(f"\nSaved {len(unmatched)} unmatched codes to boarddocs_unmatched.json")


if __name__ == "__main__":
    main()
