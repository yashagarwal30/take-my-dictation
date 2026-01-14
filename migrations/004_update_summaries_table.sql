-- Migration: Update summaries table for format selection and custom naming
-- Date: 2026-01-15
-- Description: Add format enum, custom naming, and saved status

-- Create summary format enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'summaryformat') THEN
        CREATE TYPE summaryformat AS ENUM (
            'meeting_notes',  -- Attendees, discussion, action items, next steps
            'product_spec',   -- Problem statement, solution, user stories, requirements
            'mom',            -- Minutes of Meeting - formal format
            'quick_summary'   -- Concise overview
        );
    END IF;
END $$;

-- Add new columns
ALTER TABLE summaries
ADD COLUMN IF NOT EXISTS format summaryformat DEFAULT 'quick_summary' NOT NULL,
ADD COLUMN IF NOT EXISTS custom_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS is_saved BOOLEAN DEFAULT FALSE NOT NULL;

-- Remove unique constraint on recording_id if it exists (allow multiple summaries per recording)
ALTER TABLE summaries
DROP CONSTRAINT IF EXISTS summaries_recording_id_key;

-- Create index for format for filtering
CREATE INDEX IF NOT EXISTS idx_summaries_format ON summaries(format);
CREATE INDEX IF NOT EXISTS idx_summaries_is_saved ON summaries(is_saved);
CREATE INDEX IF NOT EXISTS idx_summaries_recording_id ON summaries(recording_id);

-- Comments
COMMENT ON COLUMN summaries.format IS 'Summary format type: meeting_notes, product_spec, mom, quick_summary';
COMMENT ON COLUMN summaries.custom_name IS 'User-provided name for saved summaries';
COMMENT ON COLUMN summaries.is_saved IS 'Whether summary is saved to dashboard (paid users only)';
