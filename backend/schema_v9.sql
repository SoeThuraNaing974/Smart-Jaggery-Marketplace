-- ============================================================================
-- v9 migration — numeric payment PIN for warehouse staff (separate from login).
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v9.sql
-- ============================================================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS payment_pin_hash VARCHAR(255);
