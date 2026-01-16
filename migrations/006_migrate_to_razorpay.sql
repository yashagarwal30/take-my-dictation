-- Migration: Switch from Stripe to Razorpay payment gateway
-- Date: 2026-01-16
-- Description: Rename Stripe-specific fields to Razorpay and add new Razorpay-specific columns

-- Rename existing Stripe fields to Razorpay
ALTER TABLE users RENAME COLUMN stripe_customer_id TO razorpay_customer_id;
ALTER TABLE users RENAME COLUMN stripe_subscription_id TO razorpay_subscription_id;

-- Add new Razorpay-specific field for plan ID
ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_plan_id VARCHAR(255);

-- Drop old index and create new one
DROP INDEX IF EXISTS idx_users_stripe_customer_id;
CREATE INDEX IF NOT EXISTS idx_users_razorpay_customer_id ON users(razorpay_customer_id);

-- Add comments for documentation
COMMENT ON COLUMN users.razorpay_customer_id IS 'Customer ID from Razorpay payment gateway';
COMMENT ON COLUMN users.razorpay_subscription_id IS 'Subscription ID from Razorpay payment gateway';
COMMENT ON COLUMN users.razorpay_plan_id IS 'Razorpay plan ID for the active subscription';
