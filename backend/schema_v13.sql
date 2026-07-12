-- ============================================================================
-- v13 migration — product description (ingredients & effectiveness).
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v13.sql
-- ============================================================================
ALTER TABLE jaggery_batches  ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE product_requests ADD COLUMN IF NOT EXISTS description TEXT;
