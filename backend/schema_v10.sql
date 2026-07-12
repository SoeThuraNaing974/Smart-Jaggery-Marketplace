-- ============================================================================
-- v10 migration — emailed PIN-reset verification code (OTP) on users.
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v10.sql
-- ============================================================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS pin_reset_code    VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS pin_reset_expires TIMESTAMPTZ;
