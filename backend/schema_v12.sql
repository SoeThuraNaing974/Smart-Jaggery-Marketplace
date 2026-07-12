-- ============================================================================
-- v12 migration — add grade 'D' to jaggery_batches and product_requests.
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v12.sql
-- ============================================================================
ALTER TABLE jaggery_batches DROP CONSTRAINT IF EXISTS jaggery_batches_grade_check;
ALTER TABLE jaggery_batches ADD CONSTRAINT jaggery_batches_grade_check
    CHECK (grade IN ('A','B','C','D'));

ALTER TABLE product_requests DROP CONSTRAINT IF EXISTS product_requests_grade_check;
ALTER TABLE product_requests ADD CONSTRAINT product_requests_grade_check
    CHECK (grade IN ('A','B','C','D'));
