"""Quick probe to find ISDs on BoardDocs."""
import httpx
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

ISDS = [
    ("Allegan Area ESA", ["allegan", "alleganisd", "alleganesa", "aesa"]),
    ("Alpena-Montmorency-Alcona ESD", ["amaesd", "ama", "alpenaisd"]),
    ("Bay-Arenac ISD", ["baisd", "bayarenac", "bayisd"]),
    ("Berrien RESA", ["berrien", "berrienresa", "bresa"]),
    ("Branch ISD", ["branchisd", "branch"]),
    ("COOR ISD", ["coorisd", "coor"]),
    ("Charlevoix-Emmet ISD", ["ceisd", "charemisd", "charlevoixisd", "char"]),
    ("Clare-Gladwin RESD", ["cgresd", "claregladwin", "cgresa"]),
    ("Clinton County RESA", ["clintonresa", "clinton", "ccresa"]),
    ("Copper Country ISD", ["ccisd", "coppercountry", "copper"]),
    ("Delta-Schoolcraft ISD", ["dsisd", "deltaisd", "delta"]),
    ("Eastern Upper Peninsula ISD", ["eupisd", "eup"]),
    ("Gogebic-Ontonagon ISD", ["goisd", "gogebic"]),
    ("Heritage Southwest ISD", ["heritage", "hsisd", "heritagesw"]),
    ("Hillsdale ISD", ["hillsdaleisd", "hillsdale", "hisd"]),
    ("Huron ISD", ["huronisd", "huron", "hisd"]),
    ("Jackson County ISD", ["jcisd", "jacksonisd", "jackson"]),
    ("Kalamazoo RESA", ["kresa", "kalamazooresa", "kalamazoo"]),
    ("Lenawee ISD", ["lenaweeisd", "lenawee", "lisd"]),
    ("Livingston ESA", ["lesa", "livingstonesa", "livingston"]),
    ("Macomb ISD", ["macomb", "macombisd", "misd"]),
    ("Manistee ISD", ["manisteeisd", "manistee"]),
    ("Marquette-Alger RESA", ["maresa", "marquetteisd", "marquette"]),
    ("Mecosta-Osceola ISD", ["moisd", "mecostaisd", "mecosta"]),
    ("Menominee ISD", ["menomineeisd", "menominee"]),
    ("Midland County ESA", ["midlandesa", "mresa", "midlandisd"]),
    ("Montcalm Area ISD", ["montcalm", "montcalmisd"]),
    ("Newaygo County RESA", ["ncresa", "newaygoresa", "newaygo"]),
    ("Northwest Education Services", ["nwresd", "northwest", "nwed", "nwesa"]),
    ("Ottawa Area ISD", ["oaisd", "ottawaisd", "ottawa"]),
    ("Shiawassee RESD", ["sresd", "shiawassee", "shiawasseeresd"]),
    ("St. Clair County RESA", ["sccresa", "stclair", "stclairresa"]),
    ("St. Joseph County ISD", ["sjcisd", "stjoseph", "sjcoe"]),
    ("Tuscola ISD", ["tuscolaisd", "tuscola", "tisd"]),
    ("Van Buren ISD", ["vbisd", "vanburen", "vanburenisd"]),
    ("Wayne RESA", ["wresa", "wayneresa", "wayne"]),
    ("West Shore ESD", ["wsesd", "westshore"]),
    ("Wexford-Missaukee ISD", ["wmisd", "wexford", "wexfordisd"]),
]


def main():
    from scraper.db import get_connection, get_cursor

    found = []
    for name, codes in ISDS:
        matched = False
        for code in codes:
            url = f"https://go.boarddocs.com/mi/{code}/Board.nsf/Public"
            try:
                r = httpx.get(url, headers=HEADERS, timeout=8, follow_redirects=True)
                if r.status_code == 200 and len(r.text) > 5000:
                    print(f"FOUND: {name:40s} -> {code}")
                    found.append((name, code, url))
                    matched = True
                    break
            except Exception:
                pass
            time.sleep(0.3)  # Be polite
        if not matched:
            print(f"  NOT FOUND: {name}")

    print(f"\nFound {len(found)} ISDs on BoardDocs")

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
