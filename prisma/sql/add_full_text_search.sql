-- Full-text search setup for Meeting table
-- Run this after prisma migrate deploy

-- Add the tsvector column
ALTER TABLE "Meeting" ADD COLUMN IF NOT EXISTS "search_vector" tsvector;

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS meeting_search_idx ON "Meeting" USING gin(search_vector);

-- Create function to update search vector
-- Weight A = title, Weight B = committee name, Weight C = body text + minutes text
CREATE OR REPLACE FUNCTION meeting_search_vector_update() RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW."committeeName", '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW."plainText", '')), 'C') ||
    setweight(to_tsvector('english', coalesce(NEW."minutesText", '')), 'C');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update on INSERT and UPDATE
DROP TRIGGER IF EXISTS meeting_search_vector_trigger ON "Meeting";
CREATE TRIGGER meeting_search_vector_trigger
  BEFORE INSERT OR UPDATE OF title, "committeeName", "plainText", "minutesText"
  ON "Meeting"
  FOR EACH ROW
  EXECUTE FUNCTION meeting_search_vector_update();

-- Backfill existing rows
UPDATE "Meeting" SET search_vector =
  setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
  setweight(to_tsvector('english', coalesce("committeeName", '')), 'B') ||
  setweight(to_tsvector('english', coalesce("plainText", '')), 'C') ||
  setweight(to_tsvector('english', coalesce("minutesText", '')), 'C');

-- Backfill status for existing meetings
UPDATE "Meeting" SET status = 'APPROVED' WHERE "plainText" IS NOT NULL AND LENGTH("plainText") > 100;
UPDATE "Meeting" SET status = 'SCHEDULED' WHERE "meetingDate" > NOW() AND status = 'HELD';

-- Additional indexes
CREATE INDEX IF NOT EXISTS meeting_date_desc_idx ON "Meeting" ("meetingDate" DESC);
CREATE INDEX IF NOT EXISTS entity_county_type_idx ON "Entity" ("countyId", type);
