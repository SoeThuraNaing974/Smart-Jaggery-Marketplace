-- ============================================================================
-- v11 migration — product requests can carry an image (shown on the batch).
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v11.sql
-- ============================================================================
ALTER TABLE product_requests ADD COLUMN IF NOT EXISTS image_path VARCHAR(255);
