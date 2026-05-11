"""CLI entry point for the FOIA meeting-minutes scraper.

Usage:
    python -m scraper.main scrape [--platform BOARDDOCS] [--limit 50] [--entity-id 123]
    python -m scraper.main discover
"""

from __future__ import annotations

import os
import sys
import time
from datetime import date, timedelta
from typing import Any

import click
import structlog

from scraper.config import DEFAULT_LOOKBACK_MONTHS, STORAGE_DIR
from scraper.db import (
    complete_scrape_run,
    create_scrape_run,
    get_connection,
    get_entities_to_scrape,
    update_entity_public_url,
    update_entity_status,
    upsert_document,
    upsert_meeting,
)
from scraper.pipeline import ContentPipeline
from scraper.platforms.base import BaseScraper
from scraper.platforms.boarddocs import BoardDocsScraper
from scraper.platforms.legistar import LegistarScraper

log = structlog.get_logger()

# ------------------------------------------------------------------
# Platform registry
# ------------------------------------------------------------------

PLATFORM_SCRAPERS: dict[str, type[BaseScraper]] = {
    "BOARDDOCS": BoardDocsScraper,
    "GRANICUS": LegistarScraper,
    "LEGISTAR": LegistarScraper,
}

try:
    from scraper.platforms.static_html import StaticHtmlScraper
    PLATFORM_SCRAPERS["STATIC_HTML"] = StaticHtmlScraper
except ImportError:
    pass

try:
    from scraper.platforms.civicplus import CivicPlusScraper
    PLATFORM_SCRAPERS["CIVICPLUS_AGENDA"] = CivicPlusScraper
except ImportError:
    pass


def _get_scraper(entity: dict[str, Any]) -> BaseScraper | None:
    """Instantiate the appropriate scraper for an entity row."""
    platform = (entity.get("platform") or "").upper()
    scraper_cls = PLATFORM_SCRAPERS.get(platform)
    if scraper_cls is None:
        log.warning("main.unknown_platform", platform=platform, entity_id=entity["id"])
        return None

    scrape_config = entity.get("scrapeConfig") or {}
    if isinstance(scrape_config, str):
        import json
        try:
            scrape_config = json.loads(scrape_config)
        except json.JSONDecodeError:
            scrape_config = {}

    return scraper_cls(
        entity_id=entity["id"],
        minutes_url=entity["minutesUrl"],
        platform_code=entity.get("platformCode") or "",
        scrape_config=scrape_config,
    )


# ------------------------------------------------------------------
# CLI commands
# ------------------------------------------------------------------

@click.group()
def cli():
    """FOIA Michigan meeting-minutes scraper."""
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(0),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )


@cli.command()
@click.option(
    "--platform",
    default=None,
    type=str,
    help="Only scrape entities on this platform (e.g. BOARDDOCS).",
)
@click.option(
    "--limit",
    default=50,
    type=int,
    help="Maximum number of entities to process in this run.",
)
@click.option(
    "--entity-id",
    default=None,
    type=str,
    help="Scrape a single specific entity by its database ID.",
)
def scrape(platform: str | None, limit: int, entity_id: str | None):
    """Run the main scrape cycle.

    Fetches entities due for scraping, collects meeting minutes from
    each entity's platform, processes content through the extraction
    pipeline, and upserts results into the database.
    """
    log.info(
        "scrape.start",
        platform=platform,
        limit=limit,
        entity_id=entity_id,
    )

    entities = get_entities_to_scrape(
        platform=platform,
        limit=limit,
        entity_id=entity_id,
    )

    if not entities:
        log.info("scrape.no_entities_due")
        return

    log.info("scrape.entities_to_process", count=len(entities))

    since = date.today() - timedelta(days=DEFAULT_LOOKBACK_MONTHS * 30)
    total_meetings = 0
    total_new = 0
    errors = 0

    with ContentPipeline(STORAGE_DIR, skip_ocr=True) as pipeline:
        for entity in entities:
            entity_id_val = entity["id"]
            entity_name = entity.get("name", "unknown")
            entity_log = log.bind(entity_id=entity_id_val, entity_name=entity_name)

            scraper = _get_scraper(entity)
            if scraper is None:
                update_entity_status(
                    get_connection(),
                    entity_id_val,
                    "ERROR",
                    error=f"Unknown platform: {entity.get('platform')}",
                )
                errors += 1
                continue

            conn = get_connection()
            run_id = create_scrape_run(conn, entity_id_val)

            try:
                with scraper:
                    meetings = scraper.scrape(since=since)

                    entity_log.info("scrape.entity_meetings", count=len(meetings))
                    meetings_new = 0

                    for meeting in meetings:
                        # Fetch actual approved minutes for past meetings
                        if hasattr(scraper, "get_actual_minutes") and meeting.status != "SCHEDULED":
                            try:
                                scraper.get_actual_minutes(meeting)
                                time.sleep(1)  # Rate limit minutes requests
                            except Exception:
                                entity_log.debug(
                                    "scrape.minutes_error",
                                    source_id=meeting.source_id,
                                )

                        # Run through content pipeline and upsert
                        try:
                            processed = pipeline.process(meeting)
                            meeting_id = upsert_meeting(conn, entity_id_val, processed.to_dict())
                            if meeting_id:
                                meetings_new += 1
                        except Exception as exc:
                            entity_log.debug(
                                "scrape.meeting_process_error",
                                source_id=meeting.source_id,
                                error=f"{type(exc).__name__}: {exc}"[:200],
                            )

                    # Fetch documents (master plans, budgets, etc.)
                    if hasattr(scraper, "get_documents"):
                        try:
                            docs = scraper.get_documents()
                            for doc in docs:
                                upsert_document(conn, entity_id_val, doc)
                            if docs:
                                entity_log.info("scrape.documents", count=len(docs))
                        except Exception:
                            entity_log.debug("scrape.documents_error")
                    elif hasattr(scraper, "get_budget_documents"):
                        try:
                            budget_docs = scraper.get_budget_documents()
                            for doc in budget_docs:
                                upsert_document(conn, entity_id_val, doc)
                            if budget_docs:
                                entity_log.info("scrape.budget_docs", count=len(budget_docs))
                        except Exception:
                            entity_log.debug("scrape.budget_error")

                    # Update entity's public board URL
                    if hasattr(scraper, "public_url"):
                        try:
                            update_entity_public_url(conn, entity_id_val, scraper.public_url)
                        except Exception:
                            pass

                total_meetings += len(meetings)
                total_new += meetings_new

                update_entity_status(
                    conn, entity_id_val, "ACTIVE", meetings_found=len(meetings)
                )
                complete_scrape_run(
                    conn, run_id, "COMPLETED",
                    meetings_found=len(meetings),
                    meetings_new=meetings_new,
                )
                entity_log.info(
                    "scrape.entity_complete",
                    meetings_found=len(meetings),
                    meetings_new=meetings_new,
                )

            except Exception as exc:
                entity_log.exception("scrape.entity_error")
                errors += 1
                error_msg = f"{type(exc).__name__}: {exc}"

                try:
                    update_entity_status(
                        conn, entity_id_val, "ERROR", error=error_msg[:500]
                    )
                    complete_scrape_run(
                        conn, run_id, "FAILED", error=error_msg[:500]
                    )
                except Exception:
                    entity_log.exception("scrape.status_update_error")
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

            # Rate-limit between entities to avoid CloudFront blocks
            time.sleep(3)

    log.info(
        "scrape.complete",
        entities_processed=len(entities),
        total_meetings=total_meetings,
        total_new=total_new,
        errors=errors,
    )


@cli.command()
def discover():
    """Run platform auto-detection on entities with UNKNOWN platform.

    Visits each entity's minutes_url and tries to identify the platform
    from page content (e.g. BoardDocs markers, Granicus patterns).
    """
    log.info("discover.start")

    entities = get_entities_to_scrape(platform=None, limit=200)
    unknown = [e for e in entities if (e.get("platform") or "").upper() in ("UNKNOWN", "")]

    if not unknown:
        log.info("discover.no_unknown_entities")
        return

    log.info("discover.entities_to_check", count=len(unknown))

    import httpx
    from scraper.platforms.base import USER_AGENT

    client = httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=15,
        follow_redirects=True,
    )

    detected = 0
    try:
        for entity in unknown:
            url = entity["minutesUrl"]
            entity_log = log.bind(entity_id=entity["id"], url=url)

            try:
                resp = client.get(url)
                body = resp.text.lower()
                final_url = str(resp.url).lower()

                platform = _detect_platform(body, final_url)
                if platform:
                    entity_log.info("discover.detected", platform=platform)
                    conn = get_connection()
                    try:
                        from scraper.db import get_cursor
                        with get_cursor(conn) as cur:
                            cur.execute(
                                'UPDATE "Entity" SET platform = %s WHERE id = %s',
                                (platform, entity["id"]),
                            )
                        detected += 1
                    finally:
                        conn.close()
                else:
                    entity_log.debug("discover.no_match")

            except Exception:
                entity_log.exception("discover.error")

    finally:
        client.close()

    log.info("discover.complete", checked=len(unknown), detected=detected)


def _detect_platform(body: str, url: str) -> str | None:
    """Try to identify the meeting-minutes platform from page content."""
    # BoardDocs
    if "boarddocs.com" in url or "boarddocs" in body:
        return "BOARDDOCS"

    # Granicus / Legistar
    if "granicus.com" in url or "legistar.com" in url or "granicus" in body:
        return "GRANICUS"

    # CivicPlus / AgendaCenter
    if "civicplus.com" in url or "civicplus" in body:
        return "CIVICPLUS_AGENDA"
    if "agendacenter" in url.lower() or "agendacenter" in body:
        return "CIVICPLUS_AGENDA"

    # CivicClerk
    if "civicclerk" in url or "civicclerk" in body:
        return "CIVICCLERK"

    # IQM2
    if "iqm2.com" in url or "iqm2" in body:
        return "IQM2"

    # CivicWeb
    if "civicweb" in url:
        return "CIVICWEB"

    # PrimeGov
    if "primegov.com" in url or "primegov" in body:
        return "PRIMEGOV"

    # Static HTML heuristic: page has multiple PDF links with meeting keywords
    pdf_count = body.count(".pdf")
    minutes_keywords = sum(1 for kw in ["minutes", "meeting", "agenda"] if kw in body)
    if pdf_count >= 3 and minutes_keywords >= 2:
        return "STATIC_HTML"

    return None


def _scrape_single_entity(entity: dict[str, Any], since: date) -> dict[str, int]:
    """Scrape a single entity. Used by concurrent workers.

    Returns dict with keys: meetings_found, meetings_new, error (0 or 1).
    """
    entity_id_val = entity["id"]
    entity_name = entity.get("name", "unknown")
    entity_log = log.bind(entity_id=entity_id_val, entity_name=entity_name)

    try:
        scraper = _get_scraper(entity)
    except Exception as exc:
        entity_log.warning("scrape.scraper_init_error", error=str(exc)[:200])
        update_entity_status(
            get_connection(), entity_id_val, "ERROR",
            error=f"Scraper init failed: {exc}",
        )
        return {"meetings_found": 0, "meetings_new": 0, "error": 1}

    if scraper is None:
        update_entity_status(
            get_connection(), entity_id_val, "ERROR",
            error=f"Unknown platform: {entity.get('platform')}",
        )
        return {"meetings_found": 0, "meetings_new": 0, "error": 1}

    conn = get_connection()
    run_id = create_scrape_run(conn, entity_id_val)

    # Each worker gets its own pipeline (own HTTP client)
    pipeline = ContentPipeline(STORAGE_DIR, skip_ocr=True)

    try:
        with scraper:
            meetings = scraper.scrape(since=since)
            entity_log.info("scrape.entity_meetings", count=len(meetings))
            meetings_new = 0

            for meeting in meetings:
                if hasattr(scraper, "get_actual_minutes") and meeting.status != "SCHEDULED":
                    try:
                        scraper.get_actual_minutes(meeting)
                    except Exception:
                        pass

                try:
                    processed = pipeline.process(meeting)
                    meeting_id = upsert_meeting(conn, entity_id_val, processed.to_dict())
                    if meeting_id:
                        meetings_new += 1
                except Exception as exc:
                    entity_log.warning("scrape.meeting_error", source_id=meeting.source_id, error=str(exc)[:200])

            if hasattr(scraper, "get_documents"):
                try:
                    docs = scraper.get_documents()
                    for doc in docs:
                        upsert_document(conn, entity_id_val, doc)
                except Exception:
                    pass
            elif hasattr(scraper, "get_budget_documents"):
                try:
                    budget_docs = scraper.get_budget_documents()
                    for doc in budget_docs:
                        upsert_document(conn, entity_id_val, doc)
                except Exception:
                    pass

            if hasattr(scraper, "public_url"):
                try:
                    update_entity_public_url(conn, entity_id_val, scraper.public_url)
                except Exception:
                    pass

        update_entity_status(conn, entity_id_val, "ACTIVE", meetings_found=len(meetings))
        complete_scrape_run(conn, run_id, "COMPLETED",
                           meetings_found=len(meetings), meetings_new=meetings_new)
        entity_log.info("scrape.entity_complete",
                       meetings_found=len(meetings), meetings_new=meetings_new)

        return {"meetings_found": len(meetings), "meetings_new": meetings_new, "error": 0}

    except Exception as exc:
        entity_log.exception("scrape.entity_error")
        error_msg = f"{type(exc).__name__}: {exc}"
        try:
            update_entity_status(conn, entity_id_val, "ERROR", error=error_msg[:500])
            complete_scrape_run(conn, run_id, "FAILED", error=error_msg[:500])
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return {"meetings_found": 0, "meetings_new": 0, "error": 1}
    finally:
        pipeline.close()


@cli.command("scrape-all")
@click.option("--batch-size", default=100, type=int, help="Entities per batch.")
@click.option("--workers", default=5, type=int, help="Concurrent scraping workers.")
def scrape_all(batch_size: int, workers: int):
    """Continuously scrape all entities with concurrent workers.

    Loops through all entities with a minutesUrl that haven't been scraped
    yet, processing them in batches with multiple concurrent workers.
    OCR is skipped for speed — run `ocr-backfill` separately after.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    log.info("scrape_all.start", batch_size=batch_size, workers=workers)

    since = date.today() - timedelta(days=DEFAULT_LOOKBACK_MONTHS * 30)
    total_entities = 0
    total_meetings = 0
    total_new = 0
    total_errors = 0

    while True:
        entities = get_entities_to_scrape(platform=None, limit=batch_size)
        if not entities:
            log.info("scrape_all.done", total_entities=total_entities,
                     total_meetings=total_meetings, total_new=total_new,
                     total_errors=total_errors)
            break

        log.info("scrape_all.batch", count=len(entities), total_so_far=total_entities)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_scrape_single_entity, entity, since): entity
                for entity in entities
            }
            for future in as_completed(futures):
                entity = futures[future]
                try:
                    result = future.result()
                    total_meetings += result["meetings_found"]
                    total_new += result["meetings_new"]
                    total_errors += result["error"]
                except Exception:
                    total_errors += 1
                    log.exception("scrape_all.worker_error", entity_id=entity["id"])
                total_entities += 1

        log.info("scrape_all.batch_complete", total_entities=total_entities,
                 total_meetings=total_meetings, total_new=total_new,
                 total_errors=total_errors)


@cli.command("ocr-backfill")
@click.option("--limit", default=100, type=int, help="Max meetings to OCR.")
def ocr_backfill(limit: int):
    """Run OCR on meetings that have PDFs but no extracted text."""
    from scraper.processors.pdf import extract_pdf_text
    from scraper.processors.text import normalize_text

    log.info("ocr_backfill.start", limit=limit)

    conn = get_connection()
    try:
        from scraper.db import get_cursor
        with get_cursor(conn) as cur:
            cur.execute("""
                SELECT id, "pdfStoragePath"
                FROM "Meeting"
                WHERE "pdfStoragePath" IS NOT NULL
                  AND ("minutesText" IS NULL OR "minutesText" = '')
                  AND ("rawHtml" IS NULL OR "rawHtml" = '')
                LIMIT %s
            """, (limit,))
            meetings = cur.fetchall()

        log.info("ocr_backfill.meetings_to_process", count=len(meetings))

        processed = 0
        for meeting in meetings:
            pdf_path = meeting["pdfStoragePath"]
            if not os.path.exists(pdf_path):
                continue

            try:
                text, ocr_applied = extract_pdf_text(pdf_path, skip_ocr=False)
                if text.strip():
                    text = normalize_text(text)
                    with get_cursor(conn) as cur:
                        cur.execute("""
                            UPDATE "Meeting"
                            SET "minutesText" = %s,
                                "ocrApplied" = %s,
                                "minutesScrapedAt" = NOW(),
                                "updatedAt" = NOW()
                            WHERE id = %s
                        """, (text, ocr_applied, meeting["id"]))
                    processed += 1
                    if processed % 10 == 0:
                        log.info("ocr_backfill.progress", processed=processed)
            except Exception:
                log.debug("ocr_backfill.error", meeting_id=meeting["id"])

        log.info("ocr_backfill.complete", processed=processed)
    finally:
        conn.close()


@cli.command()
def stats():
    """Print coverage statistics across entity types and platforms."""
    conn = get_connection()
    try:
        from scraper.db import get_cursor
        with get_cursor(conn) as cur:
            # Entity coverage
            cur.execute("""
                SELECT
                    type::text as type,
                    platform::text as platform,
                    COUNT(*) as count,
                    COUNT("minutesUrl") FILTER (WHERE "minutesUrl" IS NOT NULL AND "minutesUrl" != '') as has_url,
                    COUNT("lastScrapedAt") FILTER (WHERE "lastScrapedAt" IS NOT NULL) as scraped
                FROM "Entity"
                GROUP BY type, platform
                ORDER BY type, platform
            """)
            rows = cur.fetchall()

            print(f"\n{'=' * 75}")
            print(f"{'Type':<20} {'Platform':<18} {'Count':>6} {'Has URL':>8} {'Scraped':>8}")
            print(f"{'-' * 75}")

            totals = {"count": 0, "has_url": 0, "scraped": 0}
            for r in rows:
                print(
                    f"{r['type']:<20} {r['platform']:<18} "
                    f"{r['count']:>6} {r['has_url']:>8} {r['scraped']:>8}"
                )
                totals["count"] += r["count"]
                totals["has_url"] += r["has_url"]
                totals["scraped"] += r["scraped"]

            print(f"{'-' * 75}")
            print(
                f"{'TOTAL':<20} {'':<18} "
                f"{totals['count']:>6} {totals['has_url']:>8} {totals['scraped']:>8}"
            )

            # Meeting stats
            cur.execute("""
                SELECT
                    status::text as status,
                    COUNT(*) as count,
                    COUNT("minutesText") FILTER (WHERE "minutesText" IS NOT NULL) as has_minutes
                FROM "Meeting"
                GROUP BY status
                ORDER BY status
            """)
            rows = cur.fetchall()

            print(f"\n{'=' * 50}")
            print(f"{'Status':<15} {'Meetings':>10} {'With Minutes':>12}")
            print(f"{'-' * 50}")
            for r in rows:
                print(f"{r['status']:<15} {r['count']:>10} {r['has_minutes']:>12}")

            cur.execute('SELECT COUNT(*) as total FROM "Meeting"')
            total = cur.fetchone()["total"]
            print(f"{'-' * 50}")
            print(f"{'TOTAL':<15} {total:>10}")
            print(f"{'=' * 50}")

    finally:
        conn.close()


if __name__ == "__main__":
    cli()
