"""Database access layer for the FOIA scraper.

Uses Prisma-generated camelCase column names to match the schema.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

import psycopg2
import psycopg2.extras
import structlog

from scraper.config import DATABASE_URL

log = structlog.get_logger()


def get_connection():
    """Return a new psycopg2 connection to the FOIA database."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


@contextmanager
def get_cursor(conn) -> Generator:
    """Yield a dict cursor, rolling back on error."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def get_entities_to_scrape(
    platform: str | None = None,
    limit: int = 50,
    entity_id: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch entities due for scraping from the Entity table.

    Excludes entities that have an active (running) scrape run started
    within the last 30 minutes to prevent concurrent workers from
    processing the same entity.
    """
    conn = get_connection()
    try:
        with get_cursor(conn) as cur:
            conditions = [
                '"minutesUrl" IS NOT NULL',
                "\"minutesUrl\" != ''",
                "\"scrapeStatus\" != 'PAUSED'",
                "\"scrapeStatus\" != 'UNREACHABLE'",
                "\"scrapeStatus\" != 'ERROR'",
            ]
            params: list[Any] = []

            if entity_id is not None:
                conditions.append("id = %s")
                params.append(entity_id)
            else:
                conditions.append(
                    '("lastScrapedAt" IS NULL OR "lastScrapedAt" < NOW() - INTERVAL \'24 hours\')'
                )
                # Exclude entities with active scrape runs (started < 30 min ago)
                conditions.append("""
                    id NOT IN (
                        SELECT "entityId" FROM "ScrapeRun"
                        WHERE status = 'RUNNING'
                        AND "startedAt" > NOW() - INTERVAL '30 minutes'
                    )
                """)

            if platform:
                conditions.append("platform = %s")
                params.append(platform.upper())

            where = " AND ".join(conditions)
            params.append(limit)

            query = f"""
                SELECT
                    id,
                    name,
                    type,
                    "minutesUrl",
                    platform,
                    "platformCode",
                    "scrapeConfig",
                    "lastScrapedAt",
                    "scrapeStatus"
                FROM "Entity"
                WHERE {where}
                ORDER BY "lastScrapedAt" ASC NULLS FIRST
                LIMIT %s
            """
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_meeting(conn, entity_id: str, meeting_data: dict[str, Any]) -> str | None:
    """Insert or update a meeting record.

    Uses (entityId, sourceId) as the conflict key.
    Returns the meeting id, or None on failure.
    """
    with get_cursor(conn) as cur:
        now = datetime.now(timezone.utc)

        # Generate a cuid-like ID
        import hashlib
        raw_id = f"{entity_id}_{meeting_data.get('source_id', '')}_{now.isoformat()}"
        meeting_id = "mtg_" + hashlib.md5(raw_id.encode()).hexdigest()[:16]

        cur.execute(
            """
            INSERT INTO "Meeting" (
                id,
                "entityId",
                title,
                "meetingDate",
                "committeeName",
                "meetingType",
                status,
                "sourceUrl",
                "sourceId",
                "pdfUrl",
                "pdfStoragePath",
                "rawHtml",
                "plainText",
                "minutesHtml",
                "minutesText",
                "minutesScrapedAt",
                "ocrApplied",
                "pageCount",
                "scrapedAt",
                "createdAt",
                "updatedAt"
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT ("entityId", "sourceId")
            DO UPDATE SET
                title = EXCLUDED.title,
                "meetingDate" = EXCLUDED."meetingDate",
                "committeeName" = EXCLUDED."committeeName",
                "meetingType" = EXCLUDED."meetingType",
                status = EXCLUDED.status,
                "sourceUrl" = EXCLUDED."sourceUrl",
                "pdfUrl" = EXCLUDED."pdfUrl",
                "rawHtml" = EXCLUDED."rawHtml",
                "plainText" = EXCLUDED."plainText",
                "minutesHtml" = COALESCE(EXCLUDED."minutesHtml", "Meeting"."minutesHtml"),
                "minutesText" = COALESCE(EXCLUDED."minutesText", "Meeting"."minutesText"),
                "minutesScrapedAt" = COALESCE(EXCLUDED."minutesScrapedAt", "Meeting"."minutesScrapedAt"),
                "ocrApplied" = EXCLUDED."ocrApplied",
                "pageCount" = EXCLUDED."pageCount",
                "pdfStoragePath" = EXCLUDED."pdfStoragePath",
                "updatedAt" = EXCLUDED."updatedAt"
            RETURNING id
            """,
            (
                meeting_id,
                entity_id,
                meeting_data.get("title"),
                meeting_data.get("meeting_date"),
                meeting_data.get("committee_name"),
                meeting_data.get("meeting_type"),
                meeting_data.get("status", "HELD"),
                meeting_data.get("source_url"),
                meeting_data.get("source_id"),
                meeting_data.get("pdf_url"),
                meeting_data.get("pdf_storage_path"),
                meeting_data.get("html_content"),
                meeting_data.get("raw_text"),
                meeting_data.get("minutes_html"),
                meeting_data.get("minutes_text"),
                now if meeting_data.get("minutes_text") else None,
                meeting_data.get("ocr_applied", False),
                meeting_data.get("page_count"),
                now,
                now,
                now,
            ),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def update_entity_status(
    conn,
    entity_id: str,
    status: str,
    meetings_found: int = 0,
    error: str | None = None,
) -> None:
    """Update the scrape status and lastScrapedAt timestamp for an entity."""
    with get_cursor(conn) as cur:
        cur.execute(
            """
            UPDATE "Entity"
            SET
                "scrapeStatus" = %s,
                "lastScrapedAt" = NOW(),
                "lastError" = %s,
                "updatedAt" = NOW()
            WHERE id = %s
            """,
            (status, error, entity_id),
        )


def create_scrape_run(conn, entity_id: str) -> str:
    """Create a new ScrapeRun record and return its id."""
    import hashlib
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    run_id = "run_" + hashlib.md5(f"{entity_id}_{now.isoformat()}".encode()).hexdigest()[:16]

    with get_cursor(conn) as cur:
        cur.execute(
            """
            INSERT INTO "ScrapeRun" (id, "entityId", "startedAt", status)
            VALUES (%s, %s, NOW(), 'RUNNING')
            RETURNING id
            """,
            (run_id, entity_id),
        )
        row = cur.fetchone()
        return row["id"]


def upsert_document(conn, entity_id: str, doc_data: dict[str, Any]) -> str | None:
    """Insert or update a document record.

    Uses (entityId, sourceUrl) as the conflict key.
    Returns the document id, or None on failure.
    """
    with get_cursor(conn) as cur:
        now = datetime.now(timezone.utc)

        import hashlib
        raw_id = f"{entity_id}_{doc_data.get('source_url', '')}_{now.isoformat()}"
        doc_id = "doc_" + hashlib.md5(raw_id.encode()).hexdigest()[:16]

        cur.execute(
            """
            INSERT INTO "Document" (
                id,
                "entityId",
                title,
                type,
                "fiscalYear",
                "sourceUrl",
                "pdfUrl",
                "pdfStoragePath",
                "plainText",
                "pageCount",
                "fileSize",
                "scrapedAt",
                "createdAt",
                "updatedAt"
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT ("entityId", "sourceUrl")
            DO UPDATE SET
                title = EXCLUDED.title,
                "pdfUrl" = EXCLUDED."pdfUrl",
                "pdfStoragePath" = COALESCE(EXCLUDED."pdfStoragePath", "Document"."pdfStoragePath"),
                "plainText" = COALESCE(EXCLUDED."plainText", "Document"."plainText"),
                "pageCount" = COALESCE(EXCLUDED."pageCount", "Document"."pageCount"),
                "fileSize" = COALESCE(EXCLUDED."fileSize", "Document"."fileSize"),
                "updatedAt" = EXCLUDED."updatedAt"
            RETURNING id
            """,
            (
                doc_id,
                entity_id,
                doc_data.get("title", "Untitled"),
                doc_data.get("type", "OTHER"),
                doc_data.get("fiscal_year"),
                doc_data.get("source_url"),
                doc_data.get("pdf_url"),
                doc_data.get("pdf_storage_path"),
                doc_data.get("plain_text"),
                doc_data.get("page_count"),
                doc_data.get("file_size"),
                now,
                now,
                now,
            ),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def update_entity_public_url(conn, entity_id: str, public_url: str) -> None:
    """Set the publicBoardUrl on an Entity if not already set."""
    with get_cursor(conn) as cur:
        cur.execute(
            """
            UPDATE "Entity"
            SET "publicBoardUrl" = %s, "updatedAt" = NOW()
            WHERE id = %s AND "publicBoardUrl" IS NULL
            """,
            (public_url, entity_id),
        )


def get_unknown_entities(limit: int = 100, entity_type: str | None = None) -> list[dict[str, Any]]:
    """Fetch entities with no minutesUrl for discovery purposes."""
    conn = get_connection()
    try:
        with get_cursor(conn) as cur:
            conditions = [
                '("minutesUrl" IS NULL OR "minutesUrl" = \'\')',
                "(platform::text = 'UNKNOWN' OR platform IS NULL)",
            ]
            params: list[Any] = []

            if entity_type:
                conditions.append("type::text = %s")
                params.append(entity_type)

            where = " AND ".join(conditions)
            params.append(limit)

            cur.execute(
                f"""
                SELECT id, name, type::text as type, "websiteUrl",
                       "countyId", platform::text as platform
                FROM "Entity"
                WHERE {where}
                ORDER BY type, name
                LIMIT %s
                """,
                params,
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def complete_scrape_run(
    conn,
    run_id: str,
    status: str,
    meetings_found: int = 0,
    meetings_new: int = 0,
    error: str | None = None,
) -> None:
    """Mark a scrape run as completed."""
    with get_cursor(conn) as cur:
        cur.execute(
            """
            UPDATE "ScrapeRun"
            SET
                "completedAt" = NOW(),
                status = %s,
                "meetingsFound" = %s,
                "meetingsNew" = %s,
                "errorMessage" = %s
            WHERE id = %s
            """,
            (status, meetings_found, meetings_new, error, run_id),
        )
