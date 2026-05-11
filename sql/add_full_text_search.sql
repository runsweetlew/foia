-- Add tsvector column for full-text search on Meeting table
ALTER TABLE "Meeting" ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Populate from existing text content (title + committee + minutes/plain text)
UPDATE "Meeting"
SET search_vector = to_tsvector('english',
  COALESCE(title, '') || ' ' || COALESCE("committeeName", '') || ' ' || COALESCE("minutesText", "plainText", '')
)
WHERE "minutesText" IS NOT NULL OR "plainText" IS NOT NULL;

-- GIN index for fast lookups
CREATE INDEX IF NOT EXISTS "Meeting_search_vector_idx" ON "Meeting" USING GIN (search_vector);

-- Auto-update trigger on insert/update
CREATE OR REPLACE FUNCTION meeting_search_vector_update() RETURNS trigger AS $$
BEGIN
  NEW.search_vector := to_tsvector('english',
    COALESCE(NEW.title, '') || ' ' || COALESCE(NEW."committeeName", '') || ' ' || COALESCE(NEW."minutesText", NEW."plainText", '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS meeting_search_vector_trigger ON "Meeting";
CREATE TRIGGER meeting_search_vector_trigger
  BEFORE INSERT OR UPDATE OF title, "committeeName", "minutesText", "plainText"
  ON "Meeting"
  FOR EACH ROW
  EXECUTE FUNCTION meeting_search_vector_update();
