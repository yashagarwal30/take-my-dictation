-- Migration: Update users table for trial users and usage tracking
-- Date: 2026-01-15
-- Description: Add fields for trial users, usage tracking, and subscription management

-- Add trial user fields
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_trial_user BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS trial_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS trial_minutes_used FLOAT DEFAULT 0.0 NOT NULL;

-- Add usage tracking fields
ALTER TABLE users
ADD COLUMN IF NOT EXISTS monthly_hours_limit FLOAT,
ADD COLUMN IF NOT EXISTS monthly_hours_used FLOAT DEFAULT 0.0 NOT NULL,
ADD COLUMN IF NOT EXISTS subscription_anniversary_date DATE,
ADD COLUMN IF NOT EXISTS usage_reset_at TIMESTAMP;

-- Make hashed_password nullable for trial users
ALTER TABLE users
ALTER COLUMN hashed_password DROP NOT NULL;

-- Update subscription tier enum to include BASIC instead of ENTERPRISE
-- Note: This requires handling existing data
DO $$
BEGIN
    -- Check if 'basic' value doesn't exist in the enum
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'basic'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subscriptiontier')
    ) THEN
        -- Add 'basic' to the enum
        ALTER TYPE subscriptiontier ADD VALUE 'basic';
    END IF;
END $$;

-- Update existing PRO users to BASIC if needed (optional data migration)
-- UPDATE users SET subscription_tier = 'basic' WHERE subscription_tier = 'pro';

-- Update existing ENTERPRISE users to PRO if needed (optional data migration)
-- UPDATE users SET subscription_tier = 'pro' WHERE subscription_tier = 'enterprise';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_is_trial_user ON users(is_trial_user);
CREATE INDEX IF NOT EXISTS idx_users_trial_email ON users(trial_email);
CREATE INDEX IF NOT EXISTS idx_users_subscription_anniversary ON users(subscription_anniversary_date);

-- Set monthly_hours_limit for existing users based on tier
UPDATE users
SET monthly_hours_limit = CASE
    WHEN subscription_tier = 'basic' THEN 10.0
    WHEN subscription_tier = 'pro' THEN 50.0
    ELSE NULL
END
WHERE subscription_tier IN ('basic', 'pro');

-- Comments
COMMENT ON COLUMN users.is_trial_user IS 'Whether this is a trial user (email-only, no password)';
COMMENT ON COLUMN users.trial_email IS 'Email used for trial (for tracking usage by email)';
COMMENT ON COLUMN users.trial_minutes_used IS 'Minutes used during free trial (max 10)';
COMMENT ON COLUMN users.monthly_hours_limit IS '10 hours for Basic, 50 hours for Pro';
COMMENT ON COLUMN users.monthly_hours_used IS 'Hours used in current billing cycle';
COMMENT ON COLUMN users.subscription_anniversary_date IS 'Day of month when usage resets';
COMMENT ON COLUMN users.usage_reset_at IS 'Timestamp of next usage reset';
