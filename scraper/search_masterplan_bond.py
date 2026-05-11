"""Search BoardDocs entities for meetings mentioning master plan AND bond."""

import json
import re
import sys
import time

import httpx
from bs4 import BeautifulSoup

BOARDDOCS_BASE = "https://go.boarddocs.com/mi/{code}/Board.nsf"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

AJAX_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

# Load discovered BoardDocs entities
with open("boarddocs_discovered.json") as f:
    entities = json.load(f)

# Deduplicate by code (lowercase)
seen_codes = set()
unique_entities = []
for e in entities:
    code_lower = e["code"].lower()
    if code_lower not in seen_codes:
        seen_codes.add(code_lower)
        unique_entities.append(e)

print(f"Searching {len(unique_entities)} BoardDocs entities for 'master plan' + 'bond'...", flush=True)
print("=" * 80, flush=True)

results = []

for i, entity in enumerate(unique_entities):
    code = entity["code"]
    base_url = BOARDDOCS_BASE.format(code=code)
    label = entity.get("title") or code

    # Create a fresh client per entity to get fresh cookies
    client = httpx.Client(
        timeout=20,
        follow_redirects=True,
        headers=BROWSER_HEADERS,
    )

    try:
        # Step 1: Load the public page to get cookies + committee IDs
        resp = client.get(f"{base_url}/Public")
        resp.raise_for_status()
        committee_ids = list(dict.fromkeys(re.findall(r'committeeid="([A-Z0-9]+)"', resp.text)))

        if not committee_ids:
            print(f"  [{i+1}/{len(unique_entities)}] {code}: no committees found, skipping", flush=True)
            client.close()
            time.sleep(0.5)
            continue

        # Step 2: Get meetings for each committee (using AJAX headers + referer)
        ajax_hdrs = {
            **AJAX_HEADERS,
            "Referer": f"{base_url}/Public",
            "Origin": "https://go.boarddocs.com",
        }

        all_meeting_ids = []
        for cid in committee_ids:
            try:
                resp = client.post(
                    f"{base_url}/BD-GetMeetingsList?open",
                    content=f"current_committee_id={cid}",
                    headers=ajax_hdrs,
                )
                resp.raise_for_status()
                if not resp.text.strip():
                    continue
                payload = resp.json()
                items = payload if isinstance(payload, list) else payload.get("data", [])
                for item in items:
                    uid = item.get("unique")
                    name = item.get("name", "")
                    if uid:
                        all_meeting_ids.append((uid, cid, name))
            except Exception:
                continue

        if not all_meeting_ids:
            print(f"  [{i+1}/{len(unique_entities)}] {code}: no meetings found", flush=True)
            client.close()
            time.sleep(0.5)
            continue

        # Step 3: For each meeting, fetch agenda and check for master plan + bond
        found_meetings = []
        for uid, cid, mtg_name in all_meeting_ids:
            try:
                resp = client.post(
                    f"{base_url}/PRINT-AgendaDetailed",
                    content=f"id={uid}&current_committee_id={cid}",
                    headers=ajax_hdrs,
                )
                resp.raise_for_status()
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator=" ").lower()
            except Exception:
                text = mtg_name.lower()

            has_masterplan = "master plan" in text or "masterplan" in text or "master-plan" in text or "facilities master" in text
            has_bond = "bond" in text

            if has_masterplan and has_bond:
                found_meetings.append((uid, mtg_name, cid))

            time.sleep(0.2)

        if found_meetings:
            print(f"  [{i+1}/{len(unique_entities)}] {code}: *** MATCH *** - {len(found_meetings)} meetings with master plan + bond", flush=True)
            results.append({
                "code": code,
                "title": label,
                "url": entity["url"],
                "matching_meetings": len(found_meetings),
                "meeting_names": [m[1] for m in found_meetings[:10]],
            })
        else:
            print(f"  [{i+1}/{len(unique_entities)}] {code}: no matches ({len(all_meeting_ids)} meetings checked)", flush=True)

    except Exception as exc:
        print(f"  [{i+1}/{len(unique_entities)}] {code}: ERROR - {type(exc).__name__}: {exc}", flush=True)

    client.close()
    time.sleep(0.5)

print(flush=True)
print("=" * 80, flush=True)
print(f"RESULTS: {len(results)} schools with meetings mentioning master plan + bond", flush=True)
print("=" * 80, flush=True)
for r in results:
    print(f"\n  {r['code']} - {r['title']}", flush=True)
    print(f"    URL: {r['url']}", flush=True)
    print(f"    Matching meetings: {r['matching_meetings']}", flush=True)
    for mn in r["meeting_names"]:
        print(f"      - {mn}", flush=True)

with open("masterplan_bond_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to masterplan_bond_results.json", flush=True)
