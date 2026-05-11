"""Probe additional BoardDocs codes for remaining ISDs."""
import httpx
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

REMAINING = {
    "Allegan Area ESA": ["aesa", "alleganaesa", "alleganarea"],
    "Alpena-Montmorency-Alcona ESD": ["alpena", "amaesa"],
    "Bay-Arenac ISD": ["bayisd", "ba", "barenac"],
    "Berrien RESA": ["bresa", "berrienr"],
    "COOR ISD": ["coorise", "crawford"],
    "Eastern Upper Peninsula ISD": ["eastern", "eupsd"],
    "Gogebic-Ontonagon ISD": ["goisd2", "ontonagonisd"],
    "Heritage Southwest ISD": ["hswisd", "cass", "swmisd"],
    "Hillsdale ISD": ["hillisd", "hcoe"],
    "Huron ISD": ["hursd", "huronsd"],
    "Lenawee ISD": ["lisd2", "len"],
    "Livingston ESA": ["livesa", "livsd"],
    "Manistee ISD": ["manisd"],
    "Marquette-Alger RESA": ["marea", "marq"],
    "Mecosta-Osceola ISD": ["moistd", "mecosceola"],
    "Menominee ISD": ["menisd", "men"],
    "Midland County ESA": ["mcesa", "midesa"],
    "Montcalm Area ISD": ["mcaisd", "montarea"],
    "Newaygo County RESA": ["nresa", "newaygocresa"],
    "Northwest Education Services": ["nwes", "tcisd", "tcaesa"],
    "Ottawa Area ISD": ["oaisd2", "ott"],
    "Shiawassee RESD": ["shiresd", "shi"],
    "St. Clair County RESA": ["stclairco", "sccr"],
    "St. Joseph County ISD": ["sjc", "stjoe"],
    "Tuscola ISD": ["tusisd", "tusc"],
    "Van Buren ISD": ["vanb", "vbi"],
    "Wayne RESA": ["wayneisd", "wr"],
    "West Shore ESD": ["wshore", "ws"],
    "Wexford-Missaukee ISD": ["wmiss", "wex"],
}


def main():
    from scraper.db import get_connection, get_cursor

    found = []
    for name, codes in REMAINING.items():
        for code in codes:
            url = f"https://go.boarddocs.com/mi/{code}/Board.nsf/Public"
            try:
                r = httpx.get(url, headers=HEADERS, timeout=8, follow_redirects=True)
                if r.status_code == 200 and len(r.text) > 5000:
                    print(f"FOUND: {name:40s} -> {code}")
                    found.append((name, code, url))
                    break
            except Exception:
                pass
            time.sleep(0.3)

    print(f"\nFound {len(found)} additional ISDs on BoardDocs")

    if found:
        conn = get_connection()
        updated = 0
        try:
            with get_cursor(conn) as cur:
                for name, code, url in found:
                    cur.execute(
                        """
                        UPDATE "Entity"
                        SET platform = 'BOARDDOCS',
                            "minutesUrl" = %s,
                            "platformCode" = %s,
                            "scrapeStatus" = 'PENDING',
                            "updatedAt" = NOW()
                        WHERE name = %s
                          AND type::text = 'ISD'
                          AND ("minutesUrl" IS NULL OR "minutesUrl" = '')
                        """,
                        (url, code, name),
                    )
                    if cur.rowcount > 0:
                        updated += 1
                        print(f"  Updated: {name}")
            print(f"\nUpdated {updated} ISDs in database")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
