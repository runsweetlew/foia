"""Seed county government entities (separate from the County reference table).

Each of Michigan's 83 counties has a county government that holds public
meetings. This script creates Entity records for each county government.
"""

from __future__ import annotations

import re
import sys

from scraper.db import get_connection, get_cursor


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    return s


def main():
    conn = get_connection()
    created = 0
    skipped = 0

    try:
        with get_cursor(conn) as cur:
            # Get all counties from the County table
            cur.execute('SELECT id, name FROM "County" ORDER BY name')
            counties = cur.fetchall()

            if not counties:
                print("ERROR: No counties found in database. Run county seed first.")
                sys.exit(1)

            print(f"Found {len(counties)} counties in database")

            for county in counties:
                county_id = county["id"]
                county_name = county["name"]
                entity_name = f"{county_name} County"
                slug = slugify(entity_name)
                entity_id = f"ent_{slug}"

                cur.execute(
                    """
                    INSERT INTO "Entity" (
                        id, name, slug, type, platform, "countyId",
                        "scrapeStatus", "scrapeFrequency", "isCharter",
                        "createdAt", "updatedAt"
                    ) VALUES (
                        %s, %s, %s, 'COUNTY', 'UNKNOWN', %s,
                        'PENDING', 24, false,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (slug) DO NOTHING
                    RETURNING id
                    """,
                    (entity_id, entity_name, slug, county_id),
                )
                row = cur.fetchone()
                if row:
                    created += 1
                else:
                    skipped += 1

        print(f"County entities: {created} created, {skipped} already existed")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
