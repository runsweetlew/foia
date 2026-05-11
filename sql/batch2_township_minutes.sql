-- Batch 2: Township meeting minutes URLs (next 50 alphabetically)
-- Generated 2026-05-07

-- Aetna Township (Mecosta) - has dedicated meeting minutes page with PDFs
UPDATE "Entity" SET "minutesUrl" = 'https://www.aetnatownshipmecosta.com/meeting-minutes', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Aetna Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '') AND "countyId" IN (SELECT id FROM "County" WHERE name = 'Mecosta');

-- Almer Township (Tuscola) - has website with documents section (Google Drive)
UPDATE "Entity" SET "minutesUrl" = 'https://almertownship.org/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Almer Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Beaver Township (Bay) - has yearly meeting agendas and minutes pages with PDFs
UPDATE "Entity" SET "minutesUrl" = 'https://beavertwp.com/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Beaver Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '') AND "countyId" IN (SELECT id FROM "County" WHERE name = 'Bay');

-- Blue Lake Township (Muskegon) - has board meetings page with minutes
UPDATE "Entity" SET "minutesUrl" = 'https://www.bluelaketownship.org/board-meetings/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Blue Lake Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '') AND "countyId" IN (SELECT id FROM "County" WHERE name = 'Muskegon');

-- Blue Lake Township (Kalkaska) - has meeting documents page with PDFs
UPDATE "Entity" SET "minutesUrl" = 'https://www.bluelaketwpkalkaska.gov/boards-commissions/meeting-documents/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Blue Lake Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '') AND "countyId" IN (SELECT id FROM "County" WHERE name = 'Kalkaska');

-- Cedar Creek Township (Wexford) - cedarcreektownship.org is Muskegon County, not Wexford
-- NOTE: cedarcreektownship.org appears to be the Muskegon County township (Twin Lake, MI 49457 is Muskegon County)
-- Wexford County Cedar Creek Township does not appear to have its own website with minutes online - SKIPPED

-- Cedar Township (Osceola) - has board meeting minutes PDFs on Osceola County site
UPDATE "Entity" SET "minutesUrl" = 'https://www.osceola-county.org/residents/townships/cedar_township/township_board.php', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Cedar Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Centerville Township (Leelanau) - has meeting minutes on Leelanau County site
UPDATE "Entity" SET "minutesUrl" = 'https://www.leelanau.cc/centtwpmtg.asp', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Centerville Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Central Lake Township (Antrim) - has minutes and agendas page with PDFs
UPDATE "Entity" SET "minutesUrl" = 'https://centrallaketownshipmi.gov/minutes-and-agendas/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Central Lake Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- China Township (St. Clair) - uses Documents on Demand platform
UPDATE "Entity" SET "minutesUrl" = 'https://chinatwpmi.documents-on-demand.com/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'China Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Chocolay Township (Marquette) - has meetings, minutes and notices page
UPDATE "Entity" SET "minutesUrl" = 'https://chocolay.gov/meetings-minutes-and-notices/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Chocolay Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Clarendon Township (Calhoun) - has meeting minutes by year page
UPDATE "Entity" SET "minutesUrl" = 'https://www.clarendontwp.net/copy-of-budget', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Clarendon Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Cohoctah Township (Livingston) - uses Municode meetings platform
UPDATE "Entity" SET "minutesUrl" = 'https://www.cohoctahtownship.gov/township-board', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Cohoctah Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Coloma Township (Berrien) - has official minutes pages by year
UPDATE "Entity" SET "minutesUrl" = 'https://colomatownship.org/boards-commisions/boards-committees/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Coloma Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Colon Township (St. Joseph) - has government website but minutes not confirmed online - SKIPPED

-- Columbus Township (St. Clair) - has meeting minutes on columbustwpmi.gov
UPDATE "Entity" SET "minutesUrl" = 'https://www.columbustwpmi.gov/townshipboard', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Columbus Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '') AND "countyId" IN (SELECT id FROM "County" WHERE name = 'St. Clair');

-- Comstock Township (Kalamazoo) - uses Peak Agenda (post July 2023) and MinuteTraq (pre July 2023)
UPDATE "Entity" SET "minutesUrl" = 'https://comstockmi.gov/agendas-minutes/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Comstock Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Corwith Township (Otsego) - has meeting minutes PDFs on website
UPDATE "Entity" SET "minutesUrl" = 'https://www.corwith.net/meetings-and-events.html', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Corwith Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Cottrellville Township (St. Clair) - uses Documents on Demand platform
UPDATE "Entity" SET "minutesUrl" = 'https://cottrellvilletwpmi.documents-on-demand.com/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Cottrellville Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- Crockery Township (Ottawa) - has board meeting minutes PDFs on website
UPDATE "Entity" SET "minutesUrl" = 'https://crockerytownship.gov/', platform = 'STATIC_HTML', "scrapeStatus" = 'PENDING', "updatedAt" = NOW() WHERE name = 'Crockery Township Township' AND type::text = 'TOWNSHIP' AND ("minutesUrl" IS NULL OR "minutesUrl" = '');

-- ============================================================
-- TOWNSHIPS SKIPPED (no confirmed meeting minutes URL found online):
-- ============================================================
-- Adrian Township (Lenawee) - no township website with minutes found
-- Aetna Township (Missaukee) - no website with minutes, only county listing
-- Amboy Township (Hillsdale) - no website with minutes found
-- Antioch Township (Wexford) - no website with minutes found
-- Antrim Township (Shiawassee) - website under construction
-- Arenac Township (Arenac) - no website with minutes found
-- Argyle Township (Sanilac) - county page only, no minutes posted
-- Ashland Township (Newaygo) - website exists but no minutes section found
-- Bay de Noc Township (Delta) - no minutes posted online
-- Beaver Township (Newaygo) - no website with minutes found
-- Bismarck Township (Presque Isle) - no website with minutes found
-- Bohemia Township (Ontonagon) - no website with minutes found
-- Bridgehampton Township (Sanilac) - website DNS not resolving
-- Bronson Township (Branch) - website exists but no minutes posted
-- Buckeye Township (Gladwin) - no website with minutes found
-- Burdell Township (Osceola) - no minutes posted online
-- Butterfield Township (Missaukee) - no website with minutes found
-- Caldwell Township (Missaukee) - no website with minutes found
-- California Township (Branch) - no website found
-- Cambria Township (Hillsdale) - no website with minutes found
-- Carp Lake Township (Ontonagon) - website exists but no minutes online
-- Castleton Township (Barry) - no website found
-- Chandler Township (Charlevoix) - website exists but no minutes online
-- Chandler Township (Huron) - no website found
-- Chapin Township (Saginaw) - website exists but no minutes posted
-- Clam Union Township (Missaukee) - no website with minutes found
-- Clarence Township (Calhoun) - website exists, minutes may be on News page but unconfirmed
-- Coe Township (Isabella) - website exists but no minutes section confirmed
-- Columbus Township (Luce) - columbustwpmi.gov is St. Clair County; no Luce County minutes found
-- Cornell Township (Delta) - no minutes posted online
