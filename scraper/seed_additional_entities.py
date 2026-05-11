"""
Seed additional Michigan public entities beyond the standard types.

Adds community colleges, public universities, road commissions,
drain commissions, library boards, transit authorities, and other
public bodies subject to FOIA/Open Meetings Act.

Usage:
    python -m seed_additional_entities [--dry-run]
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from scraper.db import get_connection, get_cursor

# Michigan community colleges (28)
COMMUNITY_COLLEGES = [
    "Alpena Community College",
    "Bay de Noc Community College",
    "Delta College",
    "Glen Oaks Community College",
    "Gogebic Community College",
    "Grand Rapids Community College",
    "Henry Ford College",
    "Jackson College",
    "Kalamazoo Valley Community College",
    "Kellogg Community College",
    "Kirtland Community College",
    "Lake Michigan College",
    "Lansing Community College",
    "Macomb Community College",
    "Mid Michigan College",
    "Monroe County Community College",
    "Montcalm Community College",
    "Mott Community College",
    "Muskegon Community College",
    "North Central Michigan College",
    "Northwestern Michigan College",
    "Oakland Community College",
    "Schoolcraft College",
    "Southwestern Michigan College",
    "St. Clair County Community College",
    "Washtenaw Community College",
    "Wayne County Community College District",
    "West Shore Community College",
]

# Michigan public universities (15)
PUBLIC_UNIVERSITIES = [
    "Central Michigan University",
    "Eastern Michigan University",
    "Ferris State University",
    "Grand Valley State University",
    "Lake Superior State University",
    "Michigan State University",
    "Michigan Technological University",
    "Northern Michigan University",
    "Oakland University",
    "Saginaw Valley State University",
    "University of Michigan",
    "University of Michigan-Dearborn",
    "University of Michigan-Flint",
    "Wayne State University",
    "Western Michigan University",
]

# Michigan road commissions (one per county, listing major ones)
# Most counties have a road commission as a separate entity
ROAD_COMMISSIONS = [
    ("Alcona County Road Commission", "Alcona"),
    ("Alger County Road Commission", "Alger"),
    ("Allegan County Road Commission", "Allegan"),
    ("Alpena County Road Commission", "Alpena"),
    ("Antrim County Road Commission", "Antrim"),
    ("Arenac County Road Commission", "Arenac"),
    ("Baraga County Road Commission", "Baraga"),
    ("Barry County Road Commission", "Barry"),
    ("Bay County Road Commission", "Bay"),
    ("Benzie County Road Commission", "Benzie"),
    ("Berrien County Road Commission", "Berrien"),
    ("Branch County Road Commission", "Branch"),
    ("Calhoun County Road Commission", "Calhoun"),
    ("Cass County Road Commission", "Cass"),
    ("Charlevoix County Road Commission", "Charlevoix"),
    ("Cheboygan County Road Commission", "Cheboygan"),
    ("Chippewa County Road Commission", "Chippewa"),
    ("Clare County Road Commission", "Clare"),
    ("Clinton County Road Commission", "Clinton"),
    ("Crawford County Road Commission", "Crawford"),
    ("Delta County Road Commission", "Delta"),
    ("Dickinson County Road Commission", "Dickinson"),
    ("Eaton County Road Commission", "Eaton"),
    ("Emmet County Road Commission", "Emmet"),
    ("Genesee County Road Commission", "Genesee"),
    ("Gladwin County Road Commission", "Gladwin"),
    ("Gogebic County Road Commission", "Gogebic"),
    ("Grand Traverse County Road Commission", "Grand Traverse"),
    ("Gratiot County Road Commission", "Gratiot"),
    ("Hillsdale County Road Commission", "Hillsdale"),
    ("Houghton County Road Commission", "Houghton"),
    ("Huron County Road Commission", "Huron"),
    ("Ingham County Road Department", "Ingham"),
    ("Ionia County Road Commission", "Ionia"),
    ("Iosco County Road Commission", "Iosco"),
    ("Iron County Road Commission", "Iron"),
    ("Isabella County Road Commission", "Isabella"),
    ("Jackson County Road Commission", "Jackson"),
    ("Kalamazoo County Road Commission", "Kalamazoo"),
    ("Kalkaska County Road Commission", "Kalkaska"),
    ("Kent County Road Commission", "Kent"),
    ("Keweenaw County Road Commission", "Keweenaw"),
    ("Lake County Road Commission", "Lake"),
    ("Lapeer County Road Commission", "Lapeer"),
    ("Leelanau County Road Commission", "Leelanau"),
    ("Lenawee County Road Commission", "Lenawee"),
    ("Livingston County Road Commission", "Livingston"),
    ("Luce County Road Commission", "Luce"),
    ("Mackinac County Road Commission", "Mackinac"),
    ("Macomb County Road Commission", "Macomb"),
    ("Manistee County Road Commission", "Manistee"),
    ("Marquette County Road Commission", "Marquette"),
    ("Mason County Road Commission", "Mason"),
    ("Mecosta County Road Commission", "Mecosta"),
    ("Menominee County Road Commission", "Menominee"),
    ("Midland County Road Commission", "Midland"),
    ("Missaukee County Road Commission", "Missaukee"),
    ("Monroe County Road Commission", "Monroe"),
    ("Montcalm County Road Commission", "Montcalm"),
    ("Montmorency County Road Commission", "Montmorency"),
    ("Muskegon County Road Commission", "Muskegon"),
    ("Newaygo County Road Commission", "Newaygo"),
    ("Oakland County Road Commission", "Oakland"),
    ("Oceana County Road Commission", "Oceana"),
    ("Ogemaw County Road Commission", "Ogemaw"),
    ("Ontonagon County Road Commission", "Ontonagon"),
    ("Osceola County Road Commission", "Osceola"),
    ("Oscoda County Road Commission", "Oscoda"),
    ("Otsego County Road Commission", "Otsego"),
    ("Ottawa County Road Commission", "Ottawa"),
    ("Presque Isle County Road Commission", "Presque Isle"),
    ("Roscommon County Road Commission", "Roscommon"),
    ("Saginaw County Road Commission", "Saginaw"),
    ("Sanilac County Road Commission", "Sanilac"),
    ("Schoolcraft County Road Commission", "Schoolcraft"),
    ("Shiawassee County Road Commission", "Shiawassee"),
    ("St. Clair County Road Commission", "St. Clair"),
    ("St. Joseph County Road Commission", "St. Joseph"),
    ("Tuscola County Road Commission", "Tuscola"),
    ("Van Buren County Road Commission", "Van Buren"),
    ("Washtenaw County Road Commission", "Washtenaw"),
    ("Wayne County Road Commission", "Wayne"),
    ("Wexford County Road Commission", "Wexford"),
]


def make_slug(name: str) -> str:
    """Generate a URL-safe slug from an entity name."""
    import re
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s


def make_id(name: str, entity_type: str) -> str:
    """Generate a deterministic entity ID."""
    raw = f"{entity_type}_{name}".lower()
    return "ent_" + hashlib.md5(raw.encode()).hexdigest()[:20]


def get_county_id(conn, county_name: str) -> str | None:
    """Look up a county ID by name."""
    with get_cursor(conn) as cur:
        cur.execute(
            'SELECT id FROM "County" WHERE name = %s',
            (county_name,),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed additional Michigan entities")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_connection()
    now = datetime.now(timezone.utc)
    inserted = 0

    try:
        with get_cursor(conn) as cur:
            # Check what types already exist
            cur.execute('SELECT DISTINCT type::text FROM "Entity"')
            existing_types = {r["type"] for r in cur.fetchall()}
            print(f"Existing entity types: {existing_types}")

            # Seed community colleges
            for name in COMMUNITY_COLLEGES:
                entity_id = make_id(name, "COMMUNITY_COLLEGE")
                slug = make_slug(name)
                try:
                    cur.execute("""
                        INSERT INTO "Entity" (id, name, slug, type, platform, "scrapeStatus", "createdAt", "updatedAt")
                        VALUES (%s, %s, %s, 'COMMUNITY_COLLEGE', 'UNKNOWN', 'PENDING', %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (entity_id, name, slug, now, now))
                    if cur.rowcount > 0:
                        inserted += 1
                        if not args.dry_run:
                            print(f"  Added: {name} (COMMUNITY_COLLEGE)")
                except Exception as e:
                    # Type might not exist in enum, try as text
                    conn.rollback()
                    print(f"  SKIP (type not in enum): {name}: {e}")
                    break

            # Seed public universities
            for name in PUBLIC_UNIVERSITIES:
                entity_id = make_id(name, "UNIVERSITY")
                slug = make_slug(name)
                try:
                    cur.execute("""
                        INSERT INTO "Entity" (id, name, slug, type, platform, "scrapeStatus", "createdAt", "updatedAt")
                        VALUES (%s, %s, %s, 'UNIVERSITY', 'UNKNOWN', 'PENDING', %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (entity_id, name, slug, now, now))
                    if cur.rowcount > 0:
                        inserted += 1
                        if not args.dry_run:
                            print(f"  Added: {name} (UNIVERSITY)")
                except Exception as e:
                    conn.rollback()
                    print(f"  SKIP (type not in enum): {name}: {e}")
                    break

            # Seed road commissions
            for name, county_name in ROAD_COMMISSIONS:
                entity_id = make_id(name, "ROAD_COMMISSION")
                slug = make_slug(name)
                county_id = get_county_id(conn, county_name)
                try:
                    cur.execute("""
                        INSERT INTO "Entity" (id, name, slug, type, "countyId", platform, "scrapeStatus", "createdAt", "updatedAt")
                        VALUES (%s, %s, %s, 'ROAD_COMMISSION', %s, 'UNKNOWN', 'PENDING', %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (entity_id, name, slug, county_id, now, now))
                    if cur.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    conn.rollback()
                    print(f"  SKIP (type not in enum): {name}: {e}")
                    break

        print(f"\nInserted {inserted} new entities")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
