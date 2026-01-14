-- Migration: Create email_verifications table
-- Date: 2026-01-15
-- Description: Table for storing 6-digit email verification codes

CREATE TABLE IF NOT EXISTS email_verifications (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_verifications_email ON email_verifications(email);
CREATE INDEX IF NOT EXISTS idx_email_verifications_code ON email_verifications(code);
CREATE INDEX IF NOT EXISTS idx_email_verifications_expires_at ON email_verifications(expires_at);
CREATE INDEX IF NOT EXISTS idx_email_verifications_created_at ON email_verifications(created_at);

-- Create a function to auto-delete expired codes (cleanup)
CREATE OR REPLACE FUNCTION delete_expired_verifications()
RETURNS void AS $$
BEGIN
    DELETE FROM email_verifications
    WHERE expires_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE email_verifications IS 'Stores 6-digit email verification codes for user signup';
COMMENT ON COLUMN email_verifications.code IS '6-digit verification code';
COMMENT ON COLUMN email_verifications.expires_at IS 'Code expires 15 minutes after creation';
COMMENT ON COLUMN email_verifications.verified_at IS 'Timestamp when code was verified';
COMMENT ON COLUMN email_verifications.is_used IS 'Prevents code reuse';
