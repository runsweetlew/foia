export const ENTITY_TYPE_LABELS: Record<string, string> = {
  COUNTY: "County",
  TOWNSHIP: "Township",
  CITY: "City",
  VILLAGE: "Village",
  SCHOOL_DISTRICT: "School District",
  ISD: "Intermediate School District",
  COMMUNITY_COLLEGE: "Community College",
  UNIVERSITY: "University",
  ROAD_COMMISSION: "Road Commission",
  LIBRARY: "Library",
  STATE_BOARD: "State Board/Commission",
  SPECIAL_DISTRICT: "Special District",
};

export const PLATFORM_LABELS: Record<string, string> = {
  BOARDDOCS: "BoardDocs",
  LEGISTAR: "Legistar",
  CIVICCLERK: "CivicClerk",
  CIVICPLUS_AGENDA: "CivicPlus AgendaCenter",
  IQM2: "iQM2",
  GRANICUS: "Granicus",
  CIVICWEB: "CivicWeb",
  STATIC_HTML: "Static Website",
  UNKNOWN: "Unknown",
};

export const MEETING_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  SCHEDULED: { label: "Upcoming", color: "bg-blue-50 text-blue-700" },
  HELD: { label: "Minutes Pending", color: "bg-amber-50 text-amber-700" },
  APPROVED: { label: "Minutes Available", color: "bg-green-50 text-green-700" },
  CANCELLED: { label: "Cancelled", color: "bg-red-50 text-red-700" },
};

export const MICHIGAN_COUNTIES = [
  "Alcona", "Alger", "Allegan", "Alpena", "Antrim", "Arenac", "Baraga",
  "Barry", "Bay", "Benzie", "Berrien", "Branch", "Calhoun", "Cass",
  "Charlevoix", "Cheboygan", "Chippewa", "Clare", "Clinton", "Crawford",
  "Delta", "Dickinson", "Eaton", "Emmet", "Genesee", "Gladwin", "Gogebic",
  "Grand Traverse", "Gratiot", "Hillsdale", "Houghton", "Huron", "Ingham",
  "Ionia", "Iosco", "Iron", "Isabella", "Jackson", "Kalamazoo", "Kalkaska",
  "Kent", "Keweenaw", "Lake", "Lapeer", "Leelanau", "Lenawee", "Livingston",
  "Luce", "Mackinac", "Macomb", "Manistee", "Marquette", "Mason", "Mecosta",
  "Menominee", "Midland", "Missaukee", "Monroe", "Montcalm", "Montmorency",
  "Muskegon", "Newaygo", "Oakland", "Oceana", "Ogemaw", "Ontonagon",
  "Osceola", "Oscoda", "Otsego", "Ottawa", "Presque Isle", "Roscommon",
  "Saginaw", "Sanilac", "Schoolcraft", "Shiawassee", "St. Clair",
  "St. Joseph", "Tuscola", "Van Buren", "Washtenaw", "Wayne", "Wexford",
] as const;
