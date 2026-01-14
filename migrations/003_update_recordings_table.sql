-- Migration: Update recordings table for user association and audio retention
-- Date: 2026-01-15
-- Description: Add user_id, custom naming, and audio retention fields

-- Add user association
ALTER TABLE recordings
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS custom_name VARCHAR(255);

-- Add audio retention fields
ALTER TABLE recordings
ADD COLUMN IF NOT EXISTS audio_retention_enabled BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS audio_delete_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS can_regenerate BOOLEAN DEFAULT FALSE NOT NULL;

-- Add foreign key constraint (with CASCADE delete)
ALTER TABLE recordings
ADD CONSTRAINT fk_recordings_user_id
FOREIGN KEY (user_id)
REFERENCES users(id)
ON DELETE CASCADE;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_recordings_user_id ON recordings(user_id);
CREATE INDEX IF NOT EXISTS idx_recordings_audio_delete_at ON recordings(audio_delete_at);
CREATE INDEX IF NOT EXISTS idx_recordings_can_regenerate ON recordings(can_regenerate);

-- Comments
COMMENT ON COLUMN recordings.user_id IS 'User who created this recording (nullable for trial users)';
COMMENT ON COLUMN recordings.custom_name IS 'User-provided name for saved recordings';
COMMENT ON COLUMN recordings.audio_retention_enabled IS 'Pro users can choose to save audio for 10 days';
COMMENT ON COLUMN recordings.audio_delete_at IS 'Scheduled deletion timestamp for audio file';
COMMENT ON COLUMN recordings.can_regenerate IS 'Whether audio is still available for regenerating summaries';
