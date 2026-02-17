-- ====================================
-- OAUTH CREDENTIALS STORAGE
-- ====================================
-- Stores encrypted GitHub OAuth tokens with automatic refresh capability
-- Single-row design enforced by CHECK constraint (this app has one GitHub identity)

CREATE TABLE IF NOT EXISTS github_oauth_credentials (
    id INTEGER PRIMARY KEY DEFAULT 1,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NOT NULL,
    token_expires_at TIMESTAMPTZ NOT NULL,
    refresh_token_expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT single_row CHECK (id = 1)
);

-- Create index on expiry time for quick expiry checks
CREATE INDEX IF NOT EXISTS idx_oauth_token_expiry ON github_oauth_credentials(token_expires_at);

COMMENT ON TABLE github_oauth_credentials IS 'Encrypted GitHub OAuth tokens with automatic refresh. Single-row table enforced by CHECK constraint.';
COMMENT ON COLUMN github_oauth_credentials.access_token_encrypted IS 'Fernet-encrypted GitHub OAuth access token (8hr expiry)';
COMMENT ON COLUMN github_oauth_credentials.refresh_token_encrypted IS 'Fernet-encrypted GitHub OAuth refresh token (6mo expiry)';
COMMENT ON COLUMN github_oauth_credentials.token_expires_at IS 'When the access token expires (UTC)';
COMMENT ON COLUMN github_oauth_credentials.refresh_token_expires_at IS 'When the refresh token expires (UTC)';
