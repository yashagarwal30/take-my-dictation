-- Migration: Add users table for authentication
-- This SQL script creates the users table for authentication and subscription management

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    subscription_tier VARCHAR NOT NULL DEFAULT 'free',
    stripe_customer_id VARCHAR UNIQUE,
    stripe_subscription_id VARCHAR,
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id);

-- Add check constraint for subscription tier
ALTER TABLE users ADD CONSTRAINT check_subscription_tier
    CHECK (subscription_tier IN ('free', 'pro', 'enterprise'));
