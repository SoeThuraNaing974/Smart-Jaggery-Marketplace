-- ============================================================================
-- v5 migration — per-batch jaggery photo.
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v5.sql
-- ============================================================================
ALTER TABLE jaggery_batches ADD COLUMN IF NOT EXISTS image_path VARCHAR(255);
