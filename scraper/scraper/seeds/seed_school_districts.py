"""Seed Michigan school districts and ISDs into the Entity table.

Michigan has 56 Intermediate School Districts (ISDs/RESAs/ESDs) and
approximately 540 traditional (LEA) school districts. This script
seeds all 56 ISDs and as many traditional districts as could be
compiled from public sources.

Sources:
  - MAISA (gomaisa.org) — authoritative ISD list
  - Citizens Research Council of Michigan (crcmich.org) — ISD-county mapping
  - K12 Academics — school districts by county
  - NCES Common Core of Data — district names/counties
  - Oakland Schools, Macomb County, Bay-Arenac ISD — constituent districts
"""

from __future__ import annotations

import re
import sys

from scraper.db import get_connection, get_cursor


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s


# ---------------------------------------------------------------------------
# All 56 Michigan Intermediate School Districts
# Each entry: (name, primary_county)
# For multi-county ISDs the first/primary county is used for the DB link.
# ---------------------------------------------------------------------------
ISDS: list[dict] = [
    {"name": "Allegan Area ESA", "county": "Allegan", "type": "ISD"},
    {"name": "Alpena-Montmorency-Alcona ESD", "county": "Alpena", "type": "ISD"},
    {"name": "Barry ISD", "county": "Barry", "type": "ISD"},
    {"name": "Bay-Arenac ISD", "county": "Bay", "type": "ISD"},
    {"name": "Berrien RESA", "county": "Berrien", "type": "ISD"},
    {"name": "Branch ISD", "county": "Branch", "type": "ISD"},
    {"name": "Calhoun ISD", "county": "Calhoun", "type": "ISD"},
    {"name": "Charlevoix-Emmet ISD", "county": "Charlevoix", "type": "ISD"},
    {"name": "Cheboygan-Otsego-Presque Isle ESD", "county": "Cheboygan", "type": "ISD"},
    {"name": "Clare-Gladwin RESD", "county": "Clare", "type": "ISD"},
    {"name": "Clinton County RESA", "county": "Clinton", "type": "ISD"},
    {"name": "COOR ISD", "county": "Crawford", "type": "ISD"},
    {"name": "Copper Country ISD", "county": "Houghton", "type": "ISD"},
    {"name": "Delta-Schoolcraft ISD", "county": "Delta", "type": "ISD"},
    {"name": "Dickinson-Iron ISD", "county": "Dickinson", "type": "ISD"},
    {"name": "Eastern Upper Peninsula ISD", "county": "Chippewa", "type": "ISD"},
    {"name": "Eaton RESA", "county": "Eaton", "type": "ISD"},
    {"name": "Genesee ISD", "county": "Genesee", "type": "ISD"},
    {"name": "Gogebic-Ontonagon ISD", "county": "Gogebic", "type": "ISD"},
    {"name": "Gratiot-Isabella RESD", "county": "Gratiot", "type": "ISD"},
    {"name": "Heritage Southwest ISD", "county": "Cass", "type": "ISD"},
    {"name": "Hillsdale ISD", "county": "Hillsdale", "type": "ISD"},
    {"name": "Huron ISD", "county": "Huron", "type": "ISD"},
    {"name": "Ingham ISD", "county": "Ingham", "type": "ISD"},
    {"name": "Ionia County ISD", "county": "Ionia", "type": "ISD"},
    {"name": "Iosco RESA", "county": "Iosco", "type": "ISD"},
    {"name": "Jackson County ISD", "county": "Jackson", "type": "ISD"},
    {"name": "Kalamazoo RESA", "county": "Kalamazoo", "type": "ISD"},
    {"name": "Kent ISD", "county": "Kent", "type": "ISD"},
    {"name": "Lapeer County ISD", "county": "Lapeer", "type": "ISD"},
    {"name": "Lenawee ISD", "county": "Lenawee", "type": "ISD"},
    {"name": "Livingston ESA", "county": "Livingston", "type": "ISD"},
    {"name": "Macomb ISD", "county": "Macomb", "type": "ISD"},
    {"name": "Manistee ISD", "county": "Manistee", "type": "ISD"},
    {"name": "Marquette-Alger RESA", "county": "Marquette", "type": "ISD"},
    {"name": "Mecosta-Osceola ISD", "county": "Mecosta", "type": "ISD"},
    {"name": "Menominee ISD", "county": "Menominee", "type": "ISD"},
    {"name": "Midland County ESA", "county": "Midland", "type": "ISD"},
    {"name": "Monroe County ISD", "county": "Monroe", "type": "ISD"},
    {"name": "Montcalm Area ISD", "county": "Montcalm", "type": "ISD"},
    {"name": "Muskegon Area ISD", "county": "Muskegon", "type": "ISD"},
    {"name": "Newaygo County RESA", "county": "Newaygo", "type": "ISD"},
    {"name": "Northwest Education Services", "county": "Grand Traverse", "type": "ISD"},
    {"name": "Oakland Schools", "county": "Oakland", "type": "ISD"},
    {"name": "Ottawa Area ISD", "county": "Ottawa", "type": "ISD"},
    {"name": "Saginaw ISD", "county": "Saginaw", "type": "ISD"},
    {"name": "Sanilac ISD", "county": "Sanilac", "type": "ISD"},
    {"name": "Shiawassee RESD", "county": "Shiawassee", "type": "ISD"},
    {"name": "St. Clair County RESA", "county": "St. Clair", "type": "ISD"},
    {"name": "St. Joseph County ISD", "county": "St. Joseph", "type": "ISD"},
    {"name": "Tuscola ISD", "county": "Tuscola", "type": "ISD"},
    {"name": "Van Buren ISD", "county": "Van Buren", "type": "ISD"},
    {"name": "Washtenaw ISD", "county": "Washtenaw", "type": "ISD"},
    {"name": "Wayne RESA", "county": "Wayne", "type": "ISD"},
    {"name": "West Shore ESD", "county": "Manistee", "type": "ISD"},
    {"name": "Wexford-Missaukee ISD", "county": "Wexford", "type": "ISD"},
]

# ---------------------------------------------------------------------------
# Michigan traditional (LEA) school districts, organized by county.
# ---------------------------------------------------------------------------
SCHOOL_DISTRICTS: list[dict] = [
    # --- Alcona County ---
    {"name": "Alcona Community Schools", "county": "Alcona", "type": "SCHOOL_DISTRICT"},

    # --- Alger County ---
    {"name": "Au Train-Onota Public Schools", "county": "Alger", "type": "SCHOOL_DISTRICT"},
    {"name": "Munising Public Schools", "county": "Alger", "type": "SCHOOL_DISTRICT"},
    {"name": "Burt Township Schools", "county": "Alger", "type": "SCHOOL_DISTRICT"},

    # --- Allegan County ---
    {"name": "Allegan Public Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Fennville Public Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Glenn Public Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Hamilton Community Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Hopkins Public Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Martin Public Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Otsego Public Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Plainwell Community Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Saugatuck Public Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},
    {"name": "Wayland Union Schools", "county": "Allegan", "type": "SCHOOL_DISTRICT"},

    # --- Alpena County ---
    {"name": "Alpena Public Schools", "county": "Alpena", "type": "SCHOOL_DISTRICT"},

    # --- Antrim County ---
    {"name": "Bellaire Public Schools", "county": "Antrim", "type": "SCHOOL_DISTRICT"},
    {"name": "Central Lake Public Schools", "county": "Antrim", "type": "SCHOOL_DISTRICT"},
    {"name": "Elk Rapids Schools", "county": "Antrim", "type": "SCHOOL_DISTRICT"},
    {"name": "Ellsworth Community Schools", "county": "Antrim", "type": "SCHOOL_DISTRICT"},
    {"name": "Mancelona Public Schools", "county": "Antrim", "type": "SCHOOL_DISTRICT"},
    {"name": "Alba Public Schools", "county": "Antrim", "type": "SCHOOL_DISTRICT"},

    # --- Arenac County ---
    {"name": "Arenac Eastern School District", "county": "Arenac", "type": "SCHOOL_DISTRICT"},
    {"name": "Au Gres-Sims School District", "county": "Arenac", "type": "SCHOOL_DISTRICT"},
    {"name": "Standish-Sterling Community Schools", "county": "Arenac", "type": "SCHOOL_DISTRICT"},

    # --- Baraga County ---
    {"name": "Baraga Area Schools", "county": "Baraga", "type": "SCHOOL_DISTRICT"},
    {"name": "L'Anse Area Schools", "county": "Baraga", "type": "SCHOOL_DISTRICT"},

    # --- Barry County ---
    {"name": "Delton Kellogg Schools", "county": "Barry", "type": "SCHOOL_DISTRICT"},
    {"name": "Hastings Area School District", "county": "Barry", "type": "SCHOOL_DISTRICT"},
    {"name": "Thornapple Kellogg School District", "county": "Barry", "type": "SCHOOL_DISTRICT"},

    # --- Bay County ---
    {"name": "Bangor Township Schools", "county": "Bay", "type": "SCHOOL_DISTRICT"},
    {"name": "Bay City Public Schools", "county": "Bay", "type": "SCHOOL_DISTRICT"},
    {"name": "Essexville-Hampton Public Schools", "county": "Bay", "type": "SCHOOL_DISTRICT"},
    {"name": "Pinconning Area Schools", "county": "Bay", "type": "SCHOOL_DISTRICT"},

    # --- Benzie County ---
    {"name": "Benzie County Central Schools", "county": "Benzie", "type": "SCHOOL_DISTRICT"},
    {"name": "Frankfort-Elberta Area Schools", "county": "Benzie", "type": "SCHOOL_DISTRICT"},

    # --- Berrien County ---
    {"name": "Benton Harbor Area Schools", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Berrien Springs Public Schools", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Brandywine Community Schools", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Bridgman Public Schools", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Buchanan Community Schools", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Coloma Community Schools", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Eau Claire Public Schools", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Galien Township School District", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Lakeshore School District", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "New Buffalo Area School District", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Niles Community School District", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "River Valley School District", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "St. Joseph Public Schools", "county": "Berrien", "type": "SCHOOL_DISTRICT"},
    {"name": "Watervliet School District", "county": "Berrien", "type": "SCHOOL_DISTRICT"},

    # --- Branch County ---
    {"name": "Bronson Community Schools", "county": "Branch", "type": "SCHOOL_DISTRICT"},
    {"name": "Coldwater Community Schools", "county": "Branch", "type": "SCHOOL_DISTRICT"},
    {"name": "Quincy Community Schools", "county": "Branch", "type": "SCHOOL_DISTRICT"},
    {"name": "Union City Community Schools", "county": "Branch", "type": "SCHOOL_DISTRICT"},

    # --- Calhoun County ---
    {"name": "Albion Public Schools", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},
    {"name": "Athens Area Schools", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},
    {"name": "Battle Creek Public Schools", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},
    {"name": "Harper Creek Community Schools", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},
    {"name": "Homer Community Schools", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},
    {"name": "Lakeview School District", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},
    {"name": "Marshall Public Schools", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},
    {"name": "Pennfield School District", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},
    {"name": "Tekonsha Community Schools", "county": "Calhoun", "type": "SCHOOL_DISTRICT"},

    # --- Cass County ---
    {"name": "Cassopolis Public Schools", "county": "Cass", "type": "SCHOOL_DISTRICT"},
    {"name": "Dowagiac Union Schools", "county": "Cass", "type": "SCHOOL_DISTRICT"},
    {"name": "Edwardsburg Public Schools", "county": "Cass", "type": "SCHOOL_DISTRICT"},
    {"name": "Marcellus Community Schools", "county": "Cass", "type": "SCHOOL_DISTRICT"},

    # --- Charlevoix County ---
    {"name": "Beaver Island Community School", "county": "Charlevoix", "type": "SCHOOL_DISTRICT"},
    {"name": "Boyne City Public Schools", "county": "Charlevoix", "type": "SCHOOL_DISTRICT"},
    {"name": "Charlevoix Public Schools", "county": "Charlevoix", "type": "SCHOOL_DISTRICT"},
    {"name": "East Jordan Public Schools", "county": "Charlevoix", "type": "SCHOOL_DISTRICT"},
    {"name": "Boyne Falls Public School District", "county": "Charlevoix", "type": "SCHOOL_DISTRICT"},

    # --- Cheboygan County ---
    {"name": "Cheboygan Area Schools", "county": "Cheboygan", "type": "SCHOOL_DISTRICT"},
    {"name": "Inland Lakes School District", "county": "Cheboygan", "type": "SCHOOL_DISTRICT"},
    {"name": "Mackinaw City Public Schools", "county": "Cheboygan", "type": "SCHOOL_DISTRICT"},
    {"name": "Wolverine Community Schools", "county": "Cheboygan", "type": "SCHOOL_DISTRICT"},

    # --- Chippewa County ---
    {"name": "Brimley Area Schools", "county": "Chippewa", "type": "SCHOOL_DISTRICT"},
    {"name": "DeTour Area Schools", "county": "Chippewa", "type": "SCHOOL_DISTRICT"},
    {"name": "Pickford Public Schools", "county": "Chippewa", "type": "SCHOOL_DISTRICT"},
    {"name": "Rudyard Area Schools", "county": "Chippewa", "type": "SCHOOL_DISTRICT"},
    {"name": "Sault Ste. Marie Area Schools", "county": "Chippewa", "type": "SCHOOL_DISTRICT"},

    # --- Clare County ---
    {"name": "Clare Public Schools", "county": "Clare", "type": "SCHOOL_DISTRICT"},
    {"name": "Farwell Area Schools", "county": "Clare", "type": "SCHOOL_DISTRICT"},
    {"name": "Harrison Community Schools", "county": "Clare", "type": "SCHOOL_DISTRICT"},

    # --- Clinton County ---
    {"name": "Bath Community Schools", "county": "Clinton", "type": "SCHOOL_DISTRICT"},
    {"name": "DeWitt Public Schools", "county": "Clinton", "type": "SCHOOL_DISTRICT"},
    {"name": "Fowler Public Schools", "county": "Clinton", "type": "SCHOOL_DISTRICT"},
    {"name": "Ovid-Elsie Area Schools", "county": "Clinton", "type": "SCHOOL_DISTRICT"},
    {"name": "Pewamo-Westphalia Community Schools", "county": "Clinton", "type": "SCHOOL_DISTRICT"},
    {"name": "St. Johns Public Schools", "county": "Clinton", "type": "SCHOOL_DISTRICT"},

    # --- Crawford County ---
    {"name": "Crawford AuSable Schools", "county": "Crawford", "type": "SCHOOL_DISTRICT"},

    # --- Delta County ---
    {"name": "Escanaba Area Public Schools", "county": "Delta", "type": "SCHOOL_DISTRICT"},
    {"name": "Gladstone Area Schools", "county": "Delta", "type": "SCHOOL_DISTRICT"},
    {"name": "Mid Peninsula School District", "county": "Delta", "type": "SCHOOL_DISTRICT"},
    {"name": "Rapid River Public Schools", "county": "Delta", "type": "SCHOOL_DISTRICT"},
    {"name": "Big Bay de Noc School District", "county": "Delta", "type": "SCHOOL_DISTRICT"},

    # --- Dickinson County ---
    {"name": "Breitung Township Schools", "county": "Dickinson", "type": "SCHOOL_DISTRICT"},
    {"name": "Iron Mountain Public Schools", "county": "Dickinson", "type": "SCHOOL_DISTRICT"},
    {"name": "North Dickinson County Schools", "county": "Dickinson", "type": "SCHOOL_DISTRICT"},
    {"name": "Norway-Vulcan Area Schools", "county": "Dickinson", "type": "SCHOOL_DISTRICT"},

    # --- Eaton County ---
    {"name": "Bellevue Community Schools", "county": "Eaton", "type": "SCHOOL_DISTRICT"},
    {"name": "Charlotte Public Schools", "county": "Eaton", "type": "SCHOOL_DISTRICT"},
    {"name": "Eaton Rapids Public Schools", "county": "Eaton", "type": "SCHOOL_DISTRICT"},
    {"name": "Grand Ledge Public Schools", "county": "Eaton", "type": "SCHOOL_DISTRICT"},
    {"name": "Maple Valley Schools", "county": "Eaton", "type": "SCHOOL_DISTRICT"},
    {"name": "Olivet Community Schools", "county": "Eaton", "type": "SCHOOL_DISTRICT"},
    {"name": "Potterville Public Schools", "county": "Eaton", "type": "SCHOOL_DISTRICT"},

    # --- Emmet County ---
    {"name": "Alanson Public Schools", "county": "Emmet", "type": "SCHOOL_DISTRICT"},
    {"name": "Harbor Springs School District", "county": "Emmet", "type": "SCHOOL_DISTRICT"},
    {"name": "Pellston Public Schools", "county": "Emmet", "type": "SCHOOL_DISTRICT"},
    {"name": "Public Schools of Petoskey", "county": "Emmet", "type": "SCHOOL_DISTRICT"},
    {"name": "Littlefield Public Schools", "county": "Emmet", "type": "SCHOOL_DISTRICT"},
    {"name": "Friend Public Schools", "county": "Emmet", "type": "SCHOOL_DISTRICT"},

    # --- Genesee County ---
    {"name": "Atherton Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Beecher Community School District", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Bendle Public Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Bentley Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Carman-Ainsworth Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Clio Area School District", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Davison Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Fenton Area Public Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Flint Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Flushing Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Genesee School District", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Goodrich Area Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Grand Blanc Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Kearsley Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Lake Fenton Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Lakeville Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Linden Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Montrose Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Mt. Morris Consolidated Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Swartz Creek Community Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},
    {"name": "Westwood Heights Schools", "county": "Genesee", "type": "SCHOOL_DISTRICT"},

    # --- Gladwin County ---
    {"name": "Beaverton Rural Schools", "county": "Gladwin", "type": "SCHOOL_DISTRICT"},
    {"name": "Gladwin Community Schools", "county": "Gladwin", "type": "SCHOOL_DISTRICT"},

    # --- Gogebic County ---
    {"name": "Bessemer Area School District", "county": "Gogebic", "type": "SCHOOL_DISTRICT"},
    {"name": "Ironwood Area Schools", "county": "Gogebic", "type": "SCHOOL_DISTRICT"},
    {"name": "Wakefield-Marenisco School District", "county": "Gogebic", "type": "SCHOOL_DISTRICT"},
    {"name": "Watersmeet Township School District", "county": "Gogebic", "type": "SCHOOL_DISTRICT"},

    # --- Grand Traverse County ---
    {"name": "Buckley Community Schools", "county": "Grand Traverse", "type": "SCHOOL_DISTRICT"},
    {"name": "Kingsley Area Schools", "county": "Grand Traverse", "type": "SCHOOL_DISTRICT"},
    {"name": "Traverse City Area Public Schools", "county": "Grand Traverse", "type": "SCHOOL_DISTRICT"},

    # --- Gratiot County ---
    {"name": "Alma Public Schools", "county": "Gratiot", "type": "SCHOOL_DISTRICT"},
    {"name": "Ashley Community Schools", "county": "Gratiot", "type": "SCHOOL_DISTRICT"},
    {"name": "Breckenridge Community Schools", "county": "Gratiot", "type": "SCHOOL_DISTRICT"},
    {"name": "Fulton Schools", "county": "Gratiot", "type": "SCHOOL_DISTRICT"},
    {"name": "Ithaca Public Schools", "county": "Gratiot", "type": "SCHOOL_DISTRICT"},
    {"name": "St. Louis Public Schools", "county": "Gratiot", "type": "SCHOOL_DISTRICT"},

    # --- Hillsdale County ---
    {"name": "Hillsdale Community Schools", "county": "Hillsdale", "type": "SCHOOL_DISTRICT"},
    {"name": "Jonesville Community Schools", "county": "Hillsdale", "type": "SCHOOL_DISTRICT"},
    {"name": "Litchfield Community Schools", "county": "Hillsdale", "type": "SCHOOL_DISTRICT"},
    {"name": "North Adams-Jerome Public Schools", "county": "Hillsdale", "type": "SCHOOL_DISTRICT"},
    {"name": "Pittsford Area Schools", "county": "Hillsdale", "type": "SCHOOL_DISTRICT"},
    {"name": "Reading Community Schools", "county": "Hillsdale", "type": "SCHOOL_DISTRICT"},
    {"name": "Waldron Area Schools", "county": "Hillsdale", "type": "SCHOOL_DISTRICT"},
    {"name": "Camden-Frontier Schools", "county": "Hillsdale", "type": "SCHOOL_DISTRICT"},

    # --- Houghton County ---
    {"name": "Adams Township School District", "county": "Houghton", "type": "SCHOOL_DISTRICT"},
    {"name": "Chassell Township Schools", "county": "Houghton", "type": "SCHOOL_DISTRICT"},
    {"name": "Dollar Bay-Tamarack City Area Schools", "county": "Houghton", "type": "SCHOOL_DISTRICT"},
    {"name": "Elm River Township Schools", "county": "Houghton", "type": "SCHOOL_DISTRICT"},
    {"name": "Hancock Public Schools", "county": "Houghton", "type": "SCHOOL_DISTRICT"},
    {"name": "Houghton-Portage Township Schools", "county": "Houghton", "type": "SCHOOL_DISTRICT"},
    {"name": "Lake Linden-Hubbell Public Schools", "county": "Houghton", "type": "SCHOOL_DISTRICT"},
    {"name": "Public Schools of Calumet", "county": "Houghton", "type": "SCHOOL_DISTRICT"},
    {"name": "Stanton Township Public Schools", "county": "Houghton", "type": "SCHOOL_DISTRICT"},

    # --- Huron County ---
    {"name": "Bad Axe Public Schools", "county": "Huron", "type": "SCHOOL_DISTRICT"},
    {"name": "Caseville Public Schools", "county": "Huron", "type": "SCHOOL_DISTRICT"},
    {"name": "Elkton-Pigeon-Bay Port Schools", "county": "Huron", "type": "SCHOOL_DISTRICT"},
    {"name": "Harbor Beach Community Schools", "county": "Huron", "type": "SCHOOL_DISTRICT"},
    {"name": "Laker School District", "county": "Huron", "type": "SCHOOL_DISTRICT"},
    {"name": "North Huron School District", "county": "Huron", "type": "SCHOOL_DISTRICT"},
    {"name": "Owendale-Gagetown Area Schools", "county": "Huron", "type": "SCHOOL_DISTRICT"},
    {"name": "Port Hope Community Schools", "county": "Huron", "type": "SCHOOL_DISTRICT"},
    {"name": "Ubly Community Schools", "county": "Huron", "type": "SCHOOL_DISTRICT"},

    # --- Ingham County ---
    {"name": "Dansville Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "East Lansing Public Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Haslett Public Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Holt Public Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Lansing Public School District", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Leslie Public Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Mason Public Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Okemos Public Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Stockbridge Community Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Waverly Community Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Webberville Community Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},
    {"name": "Williamston Community Schools", "county": "Ingham", "type": "SCHOOL_DISTRICT"},

    # --- Ionia County ---
    {"name": "Belding Area School District", "county": "Ionia", "type": "SCHOOL_DISTRICT"},
    {"name": "Ionia Public Schools", "county": "Ionia", "type": "SCHOOL_DISTRICT"},
    {"name": "Lakewood Public Schools", "county": "Ionia", "type": "SCHOOL_DISTRICT"},
    {"name": "Portland Public Schools", "county": "Ionia", "type": "SCHOOL_DISTRICT"},
    {"name": "Saranac Community Schools", "county": "Ionia", "type": "SCHOOL_DISTRICT"},

    # --- Iosco County ---
    {"name": "Hale Area Schools", "county": "Iosco", "type": "SCHOOL_DISTRICT"},
    {"name": "Oscoda Area Schools", "county": "Iosco", "type": "SCHOOL_DISTRICT"},
    {"name": "Tawas Area Schools", "county": "Iosco", "type": "SCHOOL_DISTRICT"},
    {"name": "Whittemore-Prescott Area Schools", "county": "Iosco", "type": "SCHOOL_DISTRICT"},

    # --- Iron County ---
    {"name": "Forest Park School District", "county": "Iron", "type": "SCHOOL_DISTRICT"},
    {"name": "West Iron County Public Schools", "county": "Iron", "type": "SCHOOL_DISTRICT"},

    # --- Isabella County ---
    {"name": "Beal City Public Schools", "county": "Isabella", "type": "SCHOOL_DISTRICT"},
    {"name": "Mt. Pleasant Public Schools", "county": "Isabella", "type": "SCHOOL_DISTRICT"},
    {"name": "Shepherd Public Schools", "county": "Isabella", "type": "SCHOOL_DISTRICT"},

    # --- Jackson County ---
    {"name": "Columbia School District", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Concord Community Schools", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "East Jackson Community Schools", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Grass Lake Community Schools", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Hanover-Horton School District", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Jackson Public Schools", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Michigan Center School District", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Napoleon Community Schools", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Northwest Community Schools", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Springport Public Schools", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Vandercook Lake Public Schools", "county": "Jackson", "type": "SCHOOL_DISTRICT"},
    {"name": "Western School District", "county": "Jackson", "type": "SCHOOL_DISTRICT"},

    # --- Kalamazoo County ---
    {"name": "Climax-Scotts Community Schools", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},
    {"name": "Comstock Public Schools", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},
    {"name": "Galesburg-Augusta Community Schools", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},
    {"name": "Gull Lake Community Schools", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},
    {"name": "Kalamazoo Public Schools", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},
    {"name": "Parchment School District", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},
    {"name": "Portage Public Schools", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},
    {"name": "Schoolcraft Community Schools", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},
    {"name": "Vicksburg Community Schools", "county": "Kalamazoo", "type": "SCHOOL_DISTRICT"},

    # --- Kalkaska County ---
    {"name": "Forest Area Community Schools", "county": "Kalkaska", "type": "SCHOOL_DISTRICT"},
    {"name": "Kalkaska Public Schools", "county": "Kalkaska", "type": "SCHOOL_DISTRICT"},
    {"name": "Excelsior Township School District", "county": "Kalkaska", "type": "SCHOOL_DISTRICT"},

    # --- Kent County ---
    {"name": "Byron Center Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Caledonia Community Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Cedar Springs Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Comstock Park Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "East Grand Rapids Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Forest Hills Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Godwin Heights Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Godfrey-Lee Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Grand Rapids Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Grandville Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Kelloggsville Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Kenowa Hills Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Kent City Community Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Kentwood Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Lowell Area Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Northview Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Rockford Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Sparta Area Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},
    {"name": "Wyoming Public Schools", "county": "Kent", "type": "SCHOOL_DISTRICT"},

    # --- Keweenaw County ---
    {"name": "Grant Township School District", "county": "Keweenaw", "type": "SCHOOL_DISTRICT"},

    # --- Lake County ---
    {"name": "Baldwin Community Schools", "county": "Lake", "type": "SCHOOL_DISTRICT"},

    # --- Lapeer County ---
    {"name": "Almont Community Schools", "county": "Lapeer", "type": "SCHOOL_DISTRICT"},
    {"name": "Dryden Community Schools", "county": "Lapeer", "type": "SCHOOL_DISTRICT"},
    {"name": "Imlay City Community Schools", "county": "Lapeer", "type": "SCHOOL_DISTRICT"},
    {"name": "Lapeer Community Schools", "county": "Lapeer", "type": "SCHOOL_DISTRICT"},
    {"name": "North Branch Area Schools", "county": "Lapeer", "type": "SCHOOL_DISTRICT"},

    # --- Leelanau County ---
    {"name": "Glen Lake Community Schools", "county": "Leelanau", "type": "SCHOOL_DISTRICT"},
    {"name": "Leland Public School District", "county": "Leelanau", "type": "SCHOOL_DISTRICT"},
    {"name": "Suttons Bay Public Schools", "county": "Leelanau", "type": "SCHOOL_DISTRICT"},
    {"name": "Northport Public School District", "county": "Leelanau", "type": "SCHOOL_DISTRICT"},

    # --- Lenawee County ---
    {"name": "Addison Community Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Adrian Public Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Blissfield Community Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Britton Deerfield Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Clinton Community Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Deerfield Public Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Hudson Area Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Madison School District", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Morenci Area Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Onsted Community Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Sand Creek Community Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},
    {"name": "Tecumseh Public Schools", "county": "Lenawee", "type": "SCHOOL_DISTRICT"},

    # --- Livingston County ---
    {"name": "Brighton Area Schools", "county": "Livingston", "type": "SCHOOL_DISTRICT"},
    {"name": "Fowlerville Community Schools", "county": "Livingston", "type": "SCHOOL_DISTRICT"},
    {"name": "Hartland Consolidated Schools", "county": "Livingston", "type": "SCHOOL_DISTRICT"},
    {"name": "Howell Public Schools", "county": "Livingston", "type": "SCHOOL_DISTRICT"},
    {"name": "Pinckney Community Schools", "county": "Livingston", "type": "SCHOOL_DISTRICT"},

    # --- Luce County ---
    {"name": "Tahquamenon Area Schools", "county": "Luce", "type": "SCHOOL_DISTRICT"},

    # --- Mackinac County ---
    {"name": "Engadine Consolidated Schools", "county": "Mackinac", "type": "SCHOOL_DISTRICT"},
    {"name": "Les Cheneaux Community Schools", "county": "Mackinac", "type": "SCHOOL_DISTRICT"},
    {"name": "Mackinac Island Public Schools", "county": "Mackinac", "type": "SCHOOL_DISTRICT"},
    {"name": "Moran Township School District", "county": "Mackinac", "type": "SCHOOL_DISTRICT"},
    {"name": "St. Ignace Area Schools", "county": "Mackinac", "type": "SCHOOL_DISTRICT"},

    # --- Macomb County ---
    {"name": "Anchor Bay School District", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Armada Area Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Center Line Public Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Chippewa Valley Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Clintondale Community Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Eastpointe Community Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Fitzgerald Public Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Fraser Public Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Lake Shore Public Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Lakeview Public Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "L'Anse Creuse Public Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Mount Clemens Community School District", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "New Haven Community Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Richmond Community Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Romeo Community Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Roseville Community Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "South Lake Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Utica Community Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Van Dyke Public Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Warren Consolidated Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},
    {"name": "Warren Woods Public Schools", "county": "Macomb", "type": "SCHOOL_DISTRICT"},

    # --- Manistee County ---
    {"name": "Bear Lake Schools", "county": "Manistee", "type": "SCHOOL_DISTRICT"},
    {"name": "Kaleva Norman Dickson Schools", "county": "Manistee", "type": "SCHOOL_DISTRICT"},
    {"name": "Manistee Area Public Schools", "county": "Manistee", "type": "SCHOOL_DISTRICT"},
    {"name": "Onekama Consolidated Schools", "county": "Manistee", "type": "SCHOOL_DISTRICT"},

    # --- Marquette County ---
    {"name": "Gwinn Area Community Schools", "county": "Marquette", "type": "SCHOOL_DISTRICT"},
    {"name": "Ishpeming Public School District", "county": "Marquette", "type": "SCHOOL_DISTRICT"},
    {"name": "Marquette Area Public Schools", "county": "Marquette", "type": "SCHOOL_DISTRICT"},
    {"name": "Negaunee Public Schools", "county": "Marquette", "type": "SCHOOL_DISTRICT"},
    {"name": "NICE Community School District", "county": "Marquette", "type": "SCHOOL_DISTRICT"},
    {"name": "Powell Township School District", "county": "Marquette", "type": "SCHOOL_DISTRICT"},
    {"name": "Republic-Michigamme Schools", "county": "Marquette", "type": "SCHOOL_DISTRICT"},
    {"name": "Wells Township School District", "county": "Marquette", "type": "SCHOOL_DISTRICT"},

    # --- Mason County ---
    {"name": "Ludington Area School District", "county": "Mason", "type": "SCHOOL_DISTRICT"},
    {"name": "Mason County Central Schools", "county": "Mason", "type": "SCHOOL_DISTRICT"},
    {"name": "Mason County Eastern Schools", "county": "Mason", "type": "SCHOOL_DISTRICT"},
    {"name": "Free Soil Community Schools", "county": "Mason", "type": "SCHOOL_DISTRICT"},

    # --- Mecosta County ---
    {"name": "Big Rapids Public Schools", "county": "Mecosta", "type": "SCHOOL_DISTRICT"},
    {"name": "Morley Stanwood Community Schools", "county": "Mecosta", "type": "SCHOOL_DISTRICT"},
    {"name": "Chippewa Hills School District", "county": "Mecosta", "type": "SCHOOL_DISTRICT"},

    # --- Menominee County ---
    {"name": "Carney-Nadeau Public Schools", "county": "Menominee", "type": "SCHOOL_DISTRICT"},
    {"name": "Menominee Area Public Schools", "county": "Menominee", "type": "SCHOOL_DISTRICT"},
    {"name": "North Central Area Schools", "county": "Menominee", "type": "SCHOOL_DISTRICT"},
    {"name": "Stephenson Area Public Schools", "county": "Menominee", "type": "SCHOOL_DISTRICT"},

    # --- Midland County ---
    {"name": "Bullock Creek School District", "county": "Midland", "type": "SCHOOL_DISTRICT"},
    {"name": "Coleman Community Schools", "county": "Midland", "type": "SCHOOL_DISTRICT"},
    {"name": "Meridian Public Schools", "county": "Midland", "type": "SCHOOL_DISTRICT"},
    {"name": "Midland Public Schools", "county": "Midland", "type": "SCHOOL_DISTRICT"},

    # --- Missaukee County ---
    {"name": "Lake City Area School District", "county": "Missaukee", "type": "SCHOOL_DISTRICT"},
    {"name": "McBain Rural Agricultural Schools", "county": "Missaukee", "type": "SCHOOL_DISTRICT"},

    # --- Monroe County ---
    {"name": "Airport Community Schools", "county": "Monroe", "type": "SCHOOL_DISTRICT"},
    {"name": "Bedford Public Schools", "county": "Monroe", "type": "SCHOOL_DISTRICT"},
    {"name": "Dundee Community Schools", "county": "Monroe", "type": "SCHOOL_DISTRICT"},
    {"name": "Ida Public Schools", "county": "Monroe", "type": "SCHOOL_DISTRICT"},
    {"name": "Jefferson Schools", "county": "Monroe", "type": "SCHOOL_DISTRICT"},
    {"name": "Mason Consolidated Schools", "county": "Monroe", "type": "SCHOOL_DISTRICT"},
    {"name": "Monroe Public Schools", "county": "Monroe", "type": "SCHOOL_DISTRICT"},
    {"name": "Summerfield School District", "county": "Monroe", "type": "SCHOOL_DISTRICT"},
    {"name": "Whiteford Agricultural Schools", "county": "Monroe", "type": "SCHOOL_DISTRICT"},

    # --- Montcalm County ---
    {"name": "Carson City-Crystal Area Schools", "county": "Montcalm", "type": "SCHOOL_DISTRICT"},
    {"name": "Central Montcalm Public Schools", "county": "Montcalm", "type": "SCHOOL_DISTRICT"},
    {"name": "Greenville Public Schools", "county": "Montcalm", "type": "SCHOOL_DISTRICT"},
    {"name": "Lakeview Community Schools", "county": "Montcalm", "type": "SCHOOL_DISTRICT"},
    {"name": "Montabella Community Schools", "county": "Montcalm", "type": "SCHOOL_DISTRICT"},
    {"name": "Tri County Area Schools", "county": "Montcalm", "type": "SCHOOL_DISTRICT"},
    {"name": "Vestaburg Community Schools", "county": "Montcalm", "type": "SCHOOL_DISTRICT"},

    # --- Montmorency County ---
    {"name": "Atlanta Community Schools", "county": "Montmorency", "type": "SCHOOL_DISTRICT"},
    {"name": "Hillman Community Schools", "county": "Montmorency", "type": "SCHOOL_DISTRICT"},

    # --- Muskegon County ---
    {"name": "Fruitport Community Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Holton Public Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Mona Shores Public Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Montague Area Public Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Muskegon Heights Public Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Muskegon Public Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "North Muskegon Public Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Oakridge Public Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Orchard View Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Ravenna Public Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Reeths-Puffer Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},
    {"name": "Whitehall District Schools", "county": "Muskegon", "type": "SCHOOL_DISTRICT"},

    # --- Newaygo County ---
    {"name": "Fremont Public Schools", "county": "Newaygo", "type": "SCHOOL_DISTRICT"},
    {"name": "Grant Public Schools", "county": "Newaygo", "type": "SCHOOL_DISTRICT"},
    {"name": "Hesperia Community Schools", "county": "Newaygo", "type": "SCHOOL_DISTRICT"},
    {"name": "Newaygo Public Schools", "county": "Newaygo", "type": "SCHOOL_DISTRICT"},
    {"name": "White Cloud Public Schools", "county": "Newaygo", "type": "SCHOOL_DISTRICT"},

    # --- Oakland County ---
    {"name": "Avondale School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Berkley School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Birmingham Public Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Bloomfield Hills Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Brandon School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Clarenceville School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Clarkston Community Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Clawson Public Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Farmington Public Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Ferndale Public Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Hazel Park Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Holly Area Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Huron Valley Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Lake Orion Community Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Lamphere Public Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Madison District Public Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Novi Community School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Oak Park Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Oxford Community Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Pontiac School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Rochester Community Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Royal Oak Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "South Lyon Community Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Southfield Public Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Troy School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Walled Lake Consolidated Schools", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "Waterford School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},
    {"name": "West Bloomfield School District", "county": "Oakland", "type": "SCHOOL_DISTRICT"},

    # --- Oceana County ---
    {"name": "Hart Public Schools", "county": "Oceana", "type": "SCHOOL_DISTRICT"},
    {"name": "Pentwater Public Schools", "county": "Oceana", "type": "SCHOOL_DISTRICT"},
    {"name": "Shelby Public Schools", "county": "Oceana", "type": "SCHOOL_DISTRICT"},
    {"name": "Walkerville Public Schools", "county": "Oceana", "type": "SCHOOL_DISTRICT"},

    # --- Ogemaw County ---
    {"name": "West Branch-Rose City Area Schools", "county": "Ogemaw", "type": "SCHOOL_DISTRICT"},

    # --- Ontonagon County ---
    {"name": "Ewen-Trout Creek Consolidated Schools", "county": "Ontonagon", "type": "SCHOOL_DISTRICT"},
    {"name": "Ontonagon Area Schools", "county": "Ontonagon", "type": "SCHOOL_DISTRICT"},
    {"name": "White Pine School District", "county": "Ontonagon", "type": "SCHOOL_DISTRICT"},

    # --- Osceola County ---
    {"name": "Evart Public Schools", "county": "Osceola", "type": "SCHOOL_DISTRICT"},
    {"name": "Marion Public Schools", "county": "Osceola", "type": "SCHOOL_DISTRICT"},
    {"name": "Pine River Area Schools", "county": "Osceola", "type": "SCHOOL_DISTRICT"},
    {"name": "Reed City Area Public Schools", "county": "Osceola", "type": "SCHOOL_DISTRICT"},

    # --- Oscoda County ---
    {"name": "Fairview Area School District", "county": "Oscoda", "type": "SCHOOL_DISTRICT"},
    {"name": "Mio AuSable Schools", "county": "Oscoda", "type": "SCHOOL_DISTRICT"},

    # --- Otsego County ---
    {"name": "Gaylord Community Schools", "county": "Otsego", "type": "SCHOOL_DISTRICT"},
    {"name": "Johannesburg-Lewiston Area Schools", "county": "Otsego", "type": "SCHOOL_DISTRICT"},
    {"name": "Vanderbilt Area Schools", "county": "Otsego", "type": "SCHOOL_DISTRICT"},

    # --- Ottawa County ---
    {"name": "Allendale Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},
    {"name": "Coopersville Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},
    {"name": "Grand Haven Area Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},
    {"name": "Holland Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},
    {"name": "Hudsonville Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},
    {"name": "Jenison Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},
    {"name": "Spring Lake Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},
    {"name": "West Ottawa Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},
    {"name": "Zeeland Public Schools", "county": "Ottawa", "type": "SCHOOL_DISTRICT"},

    # --- Presque Isle County ---
    {"name": "Onaway Area Community Schools", "county": "Presque Isle", "type": "SCHOOL_DISTRICT"},
    {"name": "Posen Consolidated Schools", "county": "Presque Isle", "type": "SCHOOL_DISTRICT"},
    {"name": "Rogers City Area Schools", "county": "Presque Isle", "type": "SCHOOL_DISTRICT"},

    # --- Roscommon County ---
    {"name": "Houghton Lake Community Schools", "county": "Roscommon", "type": "SCHOOL_DISTRICT"},
    {"name": "Roscommon Area Public Schools", "county": "Roscommon", "type": "SCHOOL_DISTRICT"},

    # --- Saginaw County ---
    {"name": "Birch Run Area Schools", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Bridgeport-Spaulding Community Schools", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Buena Vista School District", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Carrollton Public Schools", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Chesaning Union Schools", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Frankenmuth School District", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Freeland Community School District", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Hemlock Public School District", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Merrill Community Schools", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Saginaw Public Schools", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Saginaw Township Community Schools", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "St. Charles Community Schools", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Swan Valley School District", "county": "Saginaw", "type": "SCHOOL_DISTRICT"},

    # --- Sanilac County ---
    {"name": "Brown City Community Schools", "county": "Sanilac", "type": "SCHOOL_DISTRICT"},
    {"name": "Carsonville-Port Sanilac Schools", "county": "Sanilac", "type": "SCHOOL_DISTRICT"},
    {"name": "Croswell-Lexington Community Schools", "county": "Sanilac", "type": "SCHOOL_DISTRICT"},
    {"name": "Deckerville Community Schools", "county": "Sanilac", "type": "SCHOOL_DISTRICT"},
    {"name": "Marlette Community Schools", "county": "Sanilac", "type": "SCHOOL_DISTRICT"},
    {"name": "Peck Community Schools", "county": "Sanilac", "type": "SCHOOL_DISTRICT"},
    {"name": "Sandusky Community Schools", "county": "Sanilac", "type": "SCHOOL_DISTRICT"},

    # --- Schoolcraft County ---
    {"name": "Manistique Area Schools", "county": "Schoolcraft", "type": "SCHOOL_DISTRICT"},

    # --- Shiawassee County ---
    {"name": "Byron Area Schools", "county": "Shiawassee", "type": "SCHOOL_DISTRICT"},
    {"name": "Corunna Public Schools", "county": "Shiawassee", "type": "SCHOOL_DISTRICT"},
    {"name": "Durand Area Schools", "county": "Shiawassee", "type": "SCHOOL_DISTRICT"},
    {"name": "Laingsburg Community Schools", "county": "Shiawassee", "type": "SCHOOL_DISTRICT"},
    {"name": "Morrice Area Schools", "county": "Shiawassee", "type": "SCHOOL_DISTRICT"},
    {"name": "New Lothrop Area Public Schools", "county": "Shiawassee", "type": "SCHOOL_DISTRICT"},
    {"name": "Owosso Public Schools", "county": "Shiawassee", "type": "SCHOOL_DISTRICT"},
    {"name": "Perry Public Schools", "county": "Shiawassee", "type": "SCHOOL_DISTRICT"},

    # --- St. Clair County ---
    {"name": "Algonac Community School District", "county": "St. Clair", "type": "SCHOOL_DISTRICT"},
    {"name": "Capac Community Schools", "county": "St. Clair", "type": "SCHOOL_DISTRICT"},
    {"name": "East China School District", "county": "St. Clair", "type": "SCHOOL_DISTRICT"},
    {"name": "Marysville Public Schools", "county": "St. Clair", "type": "SCHOOL_DISTRICT"},
    {"name": "Memphis Community Schools", "county": "St. Clair", "type": "SCHOOL_DISTRICT"},
    {"name": "Port Huron Area School District", "county": "St. Clair", "type": "SCHOOL_DISTRICT"},
    {"name": "Yale Public Schools", "county": "St. Clair", "type": "SCHOOL_DISTRICT"},

    # --- St. Joseph County ---
    {"name": "Burr Oak Community Schools", "county": "St. Joseph", "type": "SCHOOL_DISTRICT"},
    {"name": "Centreville Public Schools", "county": "St. Joseph", "type": "SCHOOL_DISTRICT"},
    {"name": "Colon Community Schools", "county": "St. Joseph", "type": "SCHOOL_DISTRICT"},
    {"name": "Constantine Public Schools", "county": "St. Joseph", "type": "SCHOOL_DISTRICT"},
    {"name": "Mendon Community Schools", "county": "St. Joseph", "type": "SCHOOL_DISTRICT"},
    {"name": "Sturgis Public Schools", "county": "St. Joseph", "type": "SCHOOL_DISTRICT"},
    {"name": "Three Rivers Community Schools", "county": "St. Joseph", "type": "SCHOOL_DISTRICT"},
    {"name": "White Pigeon Community Schools", "county": "St. Joseph", "type": "SCHOOL_DISTRICT"},

    # --- Tuscola County ---
    {"name": "Akron-Fairgrove Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},
    {"name": "Caro Community Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},
    {"name": "Cass City Public Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},
    {"name": "Kingston Community Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},
    {"name": "Mayville Community Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},
    {"name": "Millington Community Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},
    {"name": "Reese Public Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},
    {"name": "Unionville-Sebewaing Area Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},
    {"name": "Vassar Public Schools", "county": "Tuscola", "type": "SCHOOL_DISTRICT"},

    # --- Van Buren County ---
    {"name": "Bangor Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Bloomingdale Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Covert Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Decatur Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Gobles Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Hartford Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Lawrence Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Lawton Community Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Mattawan Consolidated Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "Paw Paw Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},
    {"name": "South Haven Public Schools", "county": "Van Buren", "type": "SCHOOL_DISTRICT"},

    # --- Washtenaw County ---
    {"name": "Ann Arbor Public Schools", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Chelsea School District", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Dexter Community Schools", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Lincoln Consolidated Schools", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Manchester Community Schools", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Milan Area Schools", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Saline Area Schools", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Whitmore Lake Public Schools", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},
    {"name": "Ypsilanti Community Schools", "county": "Washtenaw", "type": "SCHOOL_DISTRICT"},

    # --- Wayne County ---
    {"name": "Allen Park Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Crestwood School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Dearborn Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Dearborn Heights School District No. 7", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Detroit Public Schools Community District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Ecorse Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Flat Rock Community Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Garden City Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Gibraltar School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Grosse Ile Township Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Grosse Pointe Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Hamtramck Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Harper Woods School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Highland Park School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Huron School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Inkster Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Lincoln Park Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Livonia Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Melvindale-Northern Allen Park Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Northville Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Plymouth-Canton Community Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Redford Union School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "River Rouge School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Riverview Community School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Romulus Community Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "South Redford School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Southgate Community School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Taylor School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Trenton Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Van Buren Public Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Wayne-Westland Community Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Westwood Community Schools", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Woodhaven-Brownstown School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},
    {"name": "Wyandotte City School District", "county": "Wayne", "type": "SCHOOL_DISTRICT"},

    # --- Wexford County ---
    {"name": "Cadillac Area Public Schools", "county": "Wexford", "type": "SCHOOL_DISTRICT"},
    {"name": "Manton Consolidated Schools", "county": "Wexford", "type": "SCHOOL_DISTRICT"},
    {"name": "Mesick Consolidated Schools", "county": "Wexford", "type": "SCHOOL_DISTRICT"},
]


ALL_ENTITIES = ISDS + SCHOOL_DISTRICTS


def main():
    conn = get_connection()
    created = 0
    skipped = 0
    errors = 0
    county_miss = 0

    try:
        with get_cursor(conn) as cur:
            # Build a lookup of county name -> county id
            cur.execute('SELECT id, name FROM "County" ORDER BY name')
            counties = cur.fetchall()
            if not counties:
                print("ERROR: No counties found in database. Run county seed first.")
                sys.exit(1)

            county_map: dict[str, str] = {}
            for c in counties:
                county_map[c["name"].lower()] = c["id"]

            print(f"Loaded {len(county_map)} counties from database")
            print(f"Seeding {len(ALL_ENTITIES)} entities ({len(ISDS)} ISDs + {len(SCHOOL_DISTRICTS)} school districts)...")
            print()

            for entity in ALL_ENTITIES:
                name = entity["name"]
                county_name = entity["county"]
                entity_type = entity["type"]

                slug = slugify(name)
                entity_id = f"ent_{slug}"

                # Look up the county ID
                county_id = county_map.get(county_name.lower())
                if not county_id:
                    print(f"  WARNING: County '{county_name}' not found for '{name}' — skipping")
                    county_miss += 1
                    continue

                try:
                    cur.execute(
                        """
                        INSERT INTO "Entity" (
                            id, name, slug, type, platform, "countyId",
                            "scrapeStatus", "scrapeFrequency", "isCharter",
                            "createdAt", "updatedAt"
                        ) VALUES (
                            %s, %s, %s, %s, 'UNKNOWN', %s,
                            'PENDING', 24, false,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (slug) DO NOTHING
                        RETURNING id
                        """,
                        (entity_id, name, slug, entity_type, county_id),
                    )
                    row = cur.fetchone()
                    if row:
                        created += 1
                        if created % 50 == 0:
                            print(f"  ... {created} created so far")
                    else:
                        skipped += 1
                except Exception as exc:
                    errors += 1
                    print(f"  ERROR inserting '{name}': {exc}")

        print()
        print("=" * 60)
        print(f"ISDs in list:              {len(ISDS)}")
        print(f"School districts in list:  {len(SCHOOL_DISTRICTS)}")
        print(f"Total entities in list:    {len(ALL_ENTITIES)}")
        print(f"Created:                   {created}")
        print(f"Already existed (skipped): {skipped}")
        print(f"County not found:          {county_miss}")
        print(f"Errors:                    {errors}")
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
