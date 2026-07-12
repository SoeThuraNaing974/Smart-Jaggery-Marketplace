-- ============================================================================
-- v8 migration — add "Yoma Pay" to the allowed subscription payment methods.
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v8.sql
-- ============================================================================
ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_method_check;
ALTER TABLE payments ADD CONSTRAINT payments_method_check
    CHECK (method IN ('kpay','wavepay','ayapay','cbpay','yomapay','bank'));
