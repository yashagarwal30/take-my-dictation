-- Migration: Fix subscriptiontier enum case consistency
-- Date: 2026-01-19
-- Description: Convert uppercase enum values to lowercase for consistency

-- Update all existing user records to use lowercase values before we change the enum
UPDATE users SET subscription_tier = 'free' WHERE subscription_tier = 'FREE';
UPDATE users SET subscription_tier = 'pro' WHERE subscription_tier = 'PRO';

-- Add lowercase versions if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'free'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subscriptiontier')
    ) THEN
        ALTER TYPE subscriptiontier ADD VALUE 'free';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'pro'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subscriptiontier')
    ) THEN
        ALTER TYPE subscriptiontier ADD VALUE 'pro';
    END IF;
END $$;

-- Remove uppercase values and create new enum type with only lowercase values
-- Note: PostgreSQL doesn't allow direct removal of enum values
-- Solution: Create new enum type and migrate

ALTER TYPE subscriptiontier RENAME TO subscriptiontier_old;

CREATE TYPE subscriptiontier AS ENUM ('free', 'basic', 'pro');

-- Drop the default temporarily
ALTER TABLE users ALTER COLUMN subscription_tier DROP DEFAULT;

-- Change the column type
ALTER TABLE users
    ALTER COLUMN subscription_tier TYPE subscriptiontier
    USING subscription_tier::text::subscriptiontier;

-- Restore the default with the new type
ALTER TABLE users ALTER COLUMN subscription_tier SET DEFAULT 'free'::subscriptiontier;

DROP TYPE subscriptiontier_old;

-- Verify the migration
DO $$
DECLARE
    enum_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO enum_count
    FROM pg_enum
    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subscriptiontier');

    IF enum_count != 3 THEN
        RAISE EXCEPTION 'Migration failed: Expected 3 enum values, got %', enum_count;
    END IF;

    RAISE NOTICE 'Migration completed successfully. Enum now has % values: free, basic, pro', enum_count;
END $$;
